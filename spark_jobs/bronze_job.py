"""
bronze_job.py — Medallion Layer: Bronze

Reads raw CDC events from 6 Kafka topics produced by Debezium,
preserves the full payload without modification, and appends to Bronze
Iceberg tables partitioned by ingestion_date.

Bronze schema (all 6 tables share the same layout):
  kafka_key           STRING   - Debezium row key (JSON)
  kafka_offset        BIGINT
  kafka_partition     INT
  kafka_topic         STRING
  kafka_timestamp     TIMESTAMP - Kafka broker timestamp
  op                  STRING   - c / r / u / d
  before_payload      STRING   - JSON of "before" field (null on inserts)
  after_payload       STRING   - JSON of "after"  field (null on deletes)
  source_db           STRING
  source_table        STRING
  source_ts_ms        BIGINT   - WAL event timestamp (ms since epoch)
  event_ts_ms         BIGINT   - Debezium processing timestamp (ms)
  raw_payload         STRING   - full Debezium JSON value
  ingestion_timestamp TIMESTAMP
  ingestion_date      DATE     - partition column

Run:
  spark-submit --master spark://spark-master:7077 /opt/spark-apps/bronze_job.py
"""

import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("bronze_job")

TABLES          = ["customers", "products", "orders", "order_items", "payments", "returns"]
KAFKA_BOOTSTRAP = "kafka:9092"
TOPIC_PREFIX    = "cdc.public"
CATALOG         = "iceberg"
SCHEMA          = "analytics"


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("cdc-bronze-ingestion").getOrCreate()


def ensure_schema(spark: SparkSession) -> None:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")


def create_bronze_table(spark: SparkSession, table: str) -> None:
    full_name = f"{CATALOG}.{SCHEMA}.bronze_{table}_cdc"
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {full_name} (
            kafka_key           STRING,
            kafka_offset        BIGINT,
            kafka_partition     INT,
            kafka_topic         STRING,
            kafka_timestamp     TIMESTAMP,
            op                  STRING,
            before_payload      STRING,
            after_payload       STRING,
            source_db           STRING,
            source_table        STRING,
            source_ts_ms        BIGINT,
            event_ts_ms         BIGINT,
            raw_payload         STRING,
            ingestion_timestamp TIMESTAMP,
            ingestion_date      DATE
        )
        USING iceberg
        PARTITIONED BY (ingestion_date)
        TBLPROPERTIES (
            'write.format.default'             = 'parquet',
            'write.parquet.compression-codec'  = 'snappy'
        )
    """)
    logger.info("Bronze table ready: %s", full_name)


def parse_and_write(spark: SparkSession, table: str, df: DataFrame, batch_id: int) -> None:
    parsed = (
        df
        .withColumn("raw_str",        F.col("value").cast(StringType()))
        # schemas.enable=false: the message IS the payload directly (no wrapper).
        # Defensively try $.payload first so the job keeps working if the connector
        # is later reconfigured with schemas enabled.
        .withColumn("payload",         F.coalesce(
            F.get_json_object(F.col("raw_str"), "$.payload"),
            F.col("raw_str"),
        ))
        .withColumn("op",              F.get_json_object(F.col("payload"), "$.op"))
        .withColumn("before_payload",  F.get_json_object(F.col("payload"), "$.before"))
        .withColumn("after_payload",   F.get_json_object(F.col("payload"), "$.after"))
        .withColumn("source_db",       F.get_json_object(F.col("payload"), "$.source.db"))
        .withColumn("source_table",    F.get_json_object(F.col("payload"), "$.source.table"))
        .withColumn("source_ts_ms",    F.get_json_object(F.col("payload"), "$.source.ts_ms").cast("bigint"))
        .withColumn("event_ts_ms",     F.get_json_object(F.col("payload"), "$.ts_ms").cast("bigint"))
        .withColumn("ingestion_timestamp", F.current_timestamp())
        .withColumn("ingestion_date",  F.current_date())
        .select(
            F.col("key").cast(StringType()).alias("kafka_key"),
            F.col("offset").alias("kafka_offset"),
            F.col("partition").alias("kafka_partition"),
            F.col("topic").alias("kafka_topic"),
            F.col("timestamp").alias("kafka_timestamp"),
            "op",
            "before_payload",
            "after_payload",
            "source_db",
            "source_table",
            "source_ts_ms",
            "event_ts_ms",
            F.col("raw_str").alias("raw_payload"),
            "ingestion_timestamp",
            "ingestion_date",
        )
    )

    # Split valid and invalid rows in a single pass to avoid recomputing the plan.
    # Rows with op=null are Debezium heartbeats or schema-change tombstones.
    valid   = parsed.filter(F.col("op").isNotNull())
    invalid = parsed.filter(F.col("op").isNull())

    # Count invalids only — cheaper than caching the full dataset. The old
    # cache/count/writeTo pattern materialised the entire enriched dataset in
    # executor memory before writing, causing OOM on large batches.
    dropped = invalid.count()
    if dropped > 0:
        logger.warning(
            "Batch %d | table=%-12s | dropped %d null-op rows (heartbeats/tombstones)",
            batch_id, table, dropped,
        )

    valid.writeTo(f"{CATALOG}.{SCHEMA}.bronze_{table}_cdc").append()
    logger.info("Batch %d | table=%-12s | written", batch_id, table)


def start_table_stream(spark: SparkSession, table: str):
    topic      = f"{TOPIC_PREFIX}.{table}"
    checkpoint = f"s3a://warehouse/checkpoints/bronze/{table}"

    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("maxOffsetsPerTrigger", 10_000)
        .option("failOnDataLoss", "false")
        .load()
    )

    return (
        raw.writeStream
        .foreachBatch(lambda df, bid: parse_and_write(spark, table, df, bid))
        .option("checkpointLocation", checkpoint)
        .trigger(processingTime="30 seconds")
        .start()
    )


def main() -> None:
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    ensure_schema(spark)
    for table in TABLES:
        create_bronze_table(spark, table)

    logger.info("Starting %d Bronze streams …", len(TABLES))
    [start_table_stream(spark, t) for t in TABLES]

    # Stop everything if any single stream fails — avoids silently running
    # 5 healthy streams while one has died without operator awareness.
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
