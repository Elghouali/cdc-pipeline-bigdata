"""
silver_job.py — Medallion Layer: Silver

Reads Bronze Iceberg tables as a streaming source, parses the Debezium
op field and before/after JSON payloads, deduplicates by Kafka offset within each key's fixed topic partition,
then applies only newer offsets via Iceberg MERGE INTO.

Silver tables produced (all in iceberg.analytics.*):
  silver_customers   — id, name, email, city, segment, signup_date
  silver_products    — id, name, category, brand, price, stock_qty
  silver_orders      — id, order_date, customer_id, status, channel
  silver_order_items — id, order_id, product_id, quantity, unit_price
  silver_payments    — id, order_id, payment_date, method, amount, status
  silver_returns     — id, order_id, return_date, reason, status

Metadata columns appended to every Silver table:
  _op           STRING   - last CDC operation
  _source_ts_ms BIGINT   - WAL event timestamp (ms)
  _kafka_partition INT  - fixed partition for the primary key
  _kafka_offset BIGINT   - last applied Kafka offset (including deletes)
  _updated_at   TIMESTAMP
  _is_deleted   BOOLEAN
  updated_date  DATE     - partition column

Run:
  spark-submit --master spark://spark-master:7077 /opt/spark-apps/silver_job.py
"""

import logging

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("silver_job")

CATALOG = "iceberg"
SCHEMA = "analytics"

# ── Entity definitions ────────────────────────────────────────────────────────
# Each entry: pk column + typed column list (name, spark_type_str)
SILVER_DEF = {
    "customers": {
        "pk": "id",
        "cols": [
            ("id", "INT"),
            ("name", "STRING"),
            ("email", "STRING"),
            ("city", "STRING"),
            ("segment", "STRING"),
            ("signup_date", "DATE"),
        ],
    },
    "products": {
        "pk": "id",
        "cols": [
            ("id", "INT"),
            ("name", "STRING"),
            ("category", "STRING"),
            ("brand", "STRING"),
            ("price", "DOUBLE"),
            ("stock_qty", "INT"),
        ],
    },
    "orders": {
        "pk": "id",
        "cols": [
            ("id", "INT"),
            ("order_date", "DATE"),
            ("customer_id", "INT"),
            ("status", "STRING"),
            ("channel", "STRING"),
        ],
    },
    "order_items": {
        "pk": "id",
        "cols": [
            ("id", "INT"),
            ("order_id", "INT"),
            ("product_id", "INT"),
            ("quantity", "INT"),
            ("unit_price", "DOUBLE"),
        ],
    },
    "payments": {
        "pk": "id",
        "cols": [
            ("id", "INT"),
            ("order_id", "INT"),
            ("payment_date", "DATE"),
            ("method", "STRING"),
            ("amount", "DOUBLE"),
            ("status", "STRING"),
        ],
    },
    "returns": {
        "pk": "id",
        "cols": [
            ("id", "INT"),
            ("order_id", "INT"),
            ("return_date", "DATE"),
            ("reason", "STRING"),
            ("status", "STRING"),
        ],
    },
}

META_COLS = [
    ("_op", "STRING"),
    ("_source_ts_ms", "BIGINT"),
    ("_kafka_partition", "INT"),
    ("_kafka_offset", "BIGINT"),
    ("_updated_at", "TIMESTAMP"),
    ("_is_deleted", "BOOLEAN"),
]


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("cdc-silver-transform").getOrCreate()


def create_silver_tables(spark: SparkSession) -> None:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
    for table, defn in SILVER_DEF.items():
        col_defs = ",\n            ".join(
            f"{c} {t}" for c, t in defn["cols"] + META_COLS + [("updated_date", "DATE")]
        )
        spark.sql(f"""
            CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.silver_{table} (
                {col_defs}
            )
            USING iceberg
            PARTITIONED BY (updated_date)
            TBLPROPERTIES (
                'write.format.default'            = 'parquet',
                'write.parquet.compression-codec' = 'snappy',
                'write.merge.mode'                = 'merge-on-read'
            )
        """)
        # CREATE IF NOT EXISTS does not migrate an existing Iceberg schema.
        # Do not silently accept rows without trustworthy Kafka ordering metadata.
        columns = set(spark.table(f"{CATALOG}.{SCHEMA}.silver_{table}").columns)
        if not {"_kafka_partition", "_kafka_offset"} <= columns:
            raise RuntimeError(
                f"silver_{table} requires an explicit rebuild or migration; "
                "see docs/SILVER_ORDERING.md"
            )
        logger.info("Silver table ready: silver_%s", table)


def extract_columns(df: DataFrame, table: str) -> DataFrame:
    """Extract typed business columns from the after/before JSON payload."""
    defn = SILVER_DEF[table]

    # For deletes use 'before', for everything else use 'after'
    payload = F.when(F.col("op") == "d", F.col("before_payload")).otherwise(
        F.col("after_payload")
    )
    df = df.withColumn("_p", payload)

    for col_name, col_type in defn["cols"]:
        raw = F.get_json_object(F.col("_p"), f"$.{col_name}")
        if col_type == "INT":
            df = df.withColumn(col_name, raw.cast("int"))
        elif col_type == "BIGINT":
            df = df.withColumn(col_name, raw.cast("long"))
        elif col_type == "DOUBLE":
            df = df.withColumn(col_name, raw.cast("double"))
        elif col_type == "DATE":
            # connect mode (our config): Debezium encodes DATE as int32 days
            # since epoch — try that first. ISO string fallbacks handle any
            # future switch to adaptive/string time.precision.mode.
            df = df.withColumn(
                col_name,
                F.coalesce(
                    F.to_date((raw.cast("long") * 86400).cast("timestamp")),
                    F.to_date(raw, "yyyy-MM-dd"),
                    F.to_date(raw, "yyyy-MM-dd'T'HH:mm:ss"),
                ),
            )
        else:
            df = df.withColumn(col_name, raw)

    return (
        df.withColumn("_op", F.col("op"))
        .withColumn("_source_ts_ms", F.col("source_ts_ms").cast("long"))
        .withColumn("_kafka_partition", F.col("kafka_partition").cast("int"))
        .withColumn("_kafka_offset", F.col("kafka_offset").cast("long"))
        .withColumn("_updated_at", F.current_timestamp())
        .withColumn("_is_deleted", F.col("op") == "d")
        .withColumn("updated_date", F.current_date())
        .drop("_p")
        .filter(F.col(defn["pk"]).isNotNull())
    )


def dedup(df: DataFrame, pk: str) -> DataFrame:
    """Keep the highest offset per PK; reject missing or ambiguous partition metadata."""
    invalid = df.filter(
        F.col("_kafka_partition").isNull()
        | F.col("_kafka_offset").isNull()
        | (F.col("_kafka_partition") < 0)
        | (F.col("_kafka_offset") < 0)
    )
    if not invalid.isEmpty():
        raise ValueError("CDC event is missing valid Kafka partition/offset")
    multiple = (
        df.groupBy(pk)
        .agg(F.countDistinct("_kafka_partition").alias("partitions"))
        .filter(F.col("partitions") > 1)
    )
    if not multiple.isEmpty():
        raise ValueError("CDC key moved between Kafka partitions; rebuild or reconcile")
    w = Window.partitionBy(pk).orderBy(F.col("_kafka_offset").desc())
    return (
        df.withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


def merge_statement(table: str, view: str) -> str:
    """Generate the guarded merge. Unknown deletes retain a tombstone watermark."""
    defn = SILVER_DEF[table]
    pk = defn["pk"]
    silver = f"{CATALOG}.{SCHEMA}.silver_{table}"
    all_cols = (
        [c for c, _ in defn["cols"]] + [m for m, _ in META_COLS] + ["updated_date"]
    )
    non_pk = [c for c in all_cols if c != pk]
    set_sql = ", ".join(f"t.{c} = s.{c}" for c in non_pk)
    ins_cols = ", ".join(all_cols)
    ins_vals = ", ".join(f"s.{c}" for c in all_cols)

    # CASE fails closed if a key's partition changes or a legacy row has no
    # watermark. Offset comparisons are meaningful only within one partition.
    newer = """CASE
        WHEN t._kafka_partition IS NULL OR t._kafka_offset IS NULL
          OR t._kafka_partition <> s._kafka_partition
        THEN CAST(raise_error('Invalid CDC partition or missing target watermark') AS BOOLEAN)
        ELSE s._kafka_offset > t._kafka_offset
        END"""
    return f"""
        MERGE INTO {silver} t
        USING global_temp.{view} s
        ON t.{pk} = s.{pk}
        WHEN MATCHED AND ({newer}) AND s._is_deleted = true THEN
            UPDATE SET t._is_deleted = true,
                       t._op = 'd',
                       t._source_ts_ms = s._source_ts_ms,
                       t._kafka_partition = s._kafka_partition,
                       t._kafka_offset = s._kafka_offset,
                       t._updated_at = s._updated_at,
                       t.updated_date = s.updated_date
        WHEN MATCHED AND ({newer}) THEN
            UPDATE SET {set_sql}
        WHEN NOT MATCHED THEN
            INSERT ({ins_cols}) VALUES ({ins_vals})
    """


def upsert(spark: SparkSession, table: str, df: DataFrame, batch_id: int) -> None:
    if df.isEmpty():
        return

    defn = SILVER_DEF[table]
    pk = defn["pk"]
    view = f"_silver_src_{table}_{batch_id}"
    parsed = extract_columns(df, table)
    deduped = dedup(parsed, pk)
    all_cols = (
        [c for c, _ in defn["cols"]] + [m for m, _ in META_COLS] + ["updated_date"]
    )
    deduped.select(all_cols).createOrReplaceGlobalTempView(view)

    try:
        spark.sql(merge_statement(table, view))
    finally:
        spark.catalog.dropGlobalTempView(view)
    logger.info("Batch %d | silver_%-12s | upserted", batch_id, table)


def start_stream(spark: SparkSession, table: str):
    bronze = f"{CATALOG}.{SCHEMA}.bronze_{table}_cdc"
    checkpoint = f"s3a://warehouse/checkpoints/silver/{table}"

    return (
        spark.readStream.format("iceberg")
        .option("stream-from-timestamp", "0")
        .load(bronze)
        .writeStream.foreachBatch(lambda df, bid: upsert(spark, table, df, bid))
        .option("checkpointLocation", checkpoint)
        .trigger(processingTime="60 seconds")
        .start()
    )


def main() -> None:
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    create_silver_tables(spark)

    logger.info("Starting %d Silver streams …", len(SILVER_DEF))
    [start_stream(spark, t) for t in SILVER_DEF]

    # Stop everything if any single stream fails.
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
