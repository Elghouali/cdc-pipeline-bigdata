"""
gold_job.py — Medallion Layer: Gold

Reads Silver Iceberg tables, applies business aggregations, and upserts
Gold fact/dimension tables via Iceberg partition overwrite.

Gold tables produced (iceberg.analytics.*):
  gold_customers        - customer 360: order count, total spend, last order
  gold_orders           - enriched order view joining customer + payment info
  gold_sales_facts      - daily KPIs by channel and customer segment
  gold_payments_summary - payment method breakdown by month
  gold_returns_summary  - return rate and reason breakdown by month

Partition column: snapshot_date DATE (today's date for all tables).
Trigger: every 5 minutes via a streaming heartbeat on silver_orders.

Run:
  spark-submit --master spark://spark-master:7077 /opt/spark-apps/gold_job.py
"""

import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gold_job")

CATALOG = "iceberg"
SCHEMA  = "analytics"


def get_spark() -> SparkSession:
    return SparkSession.builder.appName("cdc-gold-aggregation").getOrCreate()


def _ddl(table: str, body: str) -> str:
    return f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.{table} (
            {body},
            snapshot_date DATE
        )
        USING iceberg
        PARTITIONED BY (snapshot_date)
        TBLPROPERTIES (
            'write.format.default'            = 'parquet',
            'write.parquet.compression-codec' = 'snappy',
            'write.merge.mode'                = 'merge-on-read'
        )
    """


def create_gold_tables(spark: SparkSession) -> None:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

    spark.sql(_ddl("gold_customers", """
        customer_id      INT,
        name             STRING,
        city             STRING,
        segment          STRING,
        total_orders     BIGINT,
        delivered_orders BIGINT,
        cancelled_orders BIGINT,
        returned_orders  BIGINT,
        total_spent      DOUBLE,
        avg_order_value  DOUBLE,
        last_order_date  DATE,
        first_order_date DATE,
        _updated_at      TIMESTAMP
    """))

    spark.sql(_ddl("gold_orders", """
        order_id         INT,
        order_date       DATE,
        customer_id      INT,
        customer_name    STRING,
        customer_segment STRING,
        customer_city    STRING,
        status           STRING,
        channel          STRING,
        order_total      DOUBLE,
        item_count       BIGINT,
        payment_method   STRING,
        payment_status   STRING,
        has_return       BOOLEAN,
        _updated_at      TIMESTAMP
    """))

    spark.sql(_ddl("gold_sales_facts", """
        sale_date        DATE,
        channel          STRING,
        customer_segment STRING,
        product_category STRING,
        order_count      BIGINT,
        delivered_count  BIGINT,
        cancelled_count  BIGINT,
        returned_count   BIGINT,
        gross_revenue    DOUBLE,
        net_revenue      DOUBLE,
        total_items_sold BIGINT,
        avg_order_value  DOUBLE,
        _updated_at      TIMESTAMP
    """))

    spark.sql(_ddl("gold_payments_summary", """
        payment_month     STRING,
        method            STRING,
        transaction_count BIGINT,
        total_amount      DOUBLE,
        completed_amount  DOUBLE,
        refunded_amount   DOUBLE,
        pending_amount    DOUBLE,
        _updated_at       TIMESTAMP
    """))

    spark.sql(_ddl("gold_returns_summary", """
        return_month    STRING,
        reason          STRING,
        return_status   STRING,
        return_count    BIGINT,
        return_rate_pct DOUBLE,
        _updated_at     TIMESTAMP
    """))

    logger.info("All Gold tables ready.")


# ── Aggregation builders ──────────────────────────────────────────────────────

def build_gold_customers(spark: SparkSession) -> DataFrame:
    c  = spark.table(f"{CATALOG}.{SCHEMA}.silver_customers").filter("_is_deleted = false")
    o  = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")
    p  = spark.table(f"{CATALOG}.{SCHEMA}.silver_payments").filter("_is_deleted = false")

    order_agg = o.groupBy("customer_id").agg(
        F.count("id").alias("total_orders"),
        F.sum(F.when(F.col("status") == "delivered", 1).otherwise(0)).alias("delivered_orders"),
        F.sum(F.when(F.col("status") == "cancelled", 1).otherwise(0)).alias("cancelled_orders"),
        F.sum(F.when(F.col("status") == "returned",  1).otherwise(0)).alias("returned_orders"),
        F.max("order_date").alias("last_order_date"),
        F.min("order_date").alias("first_order_date"),
    )

    pay_agg = (
        p.join(o.select(F.col("id").alias("oid"), "customer_id"), p.order_id == F.col("oid"))
        .groupBy("customer_id").agg(
            F.sum("amount").alias("total_spent"),
            F.avg("amount").alias("avg_order_value"),
        )
    )

    return (
        c.join(order_agg, c.id == order_agg.customer_id, "left")
         .join(pay_agg,   c.id == pay_agg.customer_id,   "left")
         .select(
             c.id.alias("customer_id"), c.name, c.city, c.segment,
             F.coalesce(order_agg.total_orders,     F.lit(0)).alias("total_orders"),
             F.coalesce(order_agg.delivered_orders, F.lit(0)).alias("delivered_orders"),
             F.coalesce(order_agg.cancelled_orders, F.lit(0)).alias("cancelled_orders"),
             F.coalesce(order_agg.returned_orders,  F.lit(0)).alias("returned_orders"),
             F.coalesce(pay_agg.total_spent,         F.lit(0.0)).alias("total_spent"),
             F.coalesce(pay_agg.avg_order_value,     F.lit(0.0)).alias("avg_order_value"),
             order_agg.last_order_date,
             order_agg.first_order_date,
             F.current_timestamp().alias("_updated_at"),
             F.current_date().alias("snapshot_date"),
         )
    )


def build_gold_orders(spark: SparkSession) -> DataFrame:
    o  = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")
    c  = spark.table(f"{CATALOG}.{SCHEMA}.silver_customers").filter("_is_deleted = false")
    oi = spark.table(f"{CATALOG}.{SCHEMA}.silver_order_items").filter("_is_deleted = false")
    p  = spark.table(f"{CATALOG}.{SCHEMA}.silver_payments").filter("_is_deleted = false")
    r  = spark.table(f"{CATALOG}.{SCHEMA}.silver_returns").filter("_is_deleted = false")

    items = oi.groupBy("order_id").agg(
        F.sum(F.col("quantity") * F.col("unit_price")).alias("order_total"),
        F.sum("quantity").alias("item_count"),
    )

    return (
        o
        .join(c.select(F.col("id").alias("cid"), "name", "segment", "city"),
              o.customer_id == F.col("cid"), "left")
        .join(items, o.id == items.order_id, "left")
        .join(p.select(F.col("order_id").alias("pid"),
                       F.col("method").alias("pay_method"),
                       F.col("status").alias("pay_status")),
              o.id == F.col("pid"), "left")
        .join(r.select(F.col("order_id").alias("rid")).distinct(),
              o.id == F.col("rid"), "left")
        .select(
            o.id.alias("order_id"),   o.order_date,  o.customer_id,
            F.col("name").alias("customer_name"),
            F.col("segment").alias("customer_segment"),
            F.col("city").alias("customer_city"),
            o.status, o.channel,
            F.coalesce("order_total", F.lit(0.0)).alias("order_total"),
            F.coalesce("item_count",  F.lit(0)).alias("item_count"),
            F.col("pay_method").alias("payment_method"),
            F.col("pay_status").alias("payment_status"),
            F.col("rid").isNotNull().alias("has_return"),
            F.current_timestamp().alias("_updated_at"),
            F.current_date().alias("snapshot_date"),
        )
    )


def build_gold_sales_facts(spark: SparkSession) -> DataFrame:
    o  = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")
    c  = spark.table(f"{CATALOG}.{SCHEMA}.silver_customers").filter("_is_deleted = false")
    oi = spark.table(f"{CATALOG}.{SCHEMA}.silver_order_items").filter("_is_deleted = false")
    pr = spark.table(f"{CATALOG}.{SCHEMA}.silver_products").filter("_is_deleted = false")

    enriched = (
        oi
        .join(pr.select(F.col("id").alias("prid"), "category"), oi.product_id == F.col("prid"), "left")
        .join(o.select(F.col("id").alias("oid"), "order_date", "customer_id", "status", "channel"),
              oi.order_id == F.col("oid"), "left")
        .join(c.select(F.col("id").alias("cid"), "segment"),
              F.col("customer_id") == F.col("cid"), "left")
    )

    return (
        enriched.groupBy(
            F.col("order_date").alias("sale_date"),
            "channel",
            F.col("segment").alias("customer_segment"),
            F.col("category").alias("product_category"),
        ).agg(
            F.countDistinct(oi.order_id).alias("order_count"),
            F.sum(F.when(F.col("status") == "delivered", 1).otherwise(0)).alias("delivered_count"),
            F.sum(F.when(F.col("status") == "cancelled", 1).otherwise(0)).alias("cancelled_count"),
            F.sum(F.when(F.col("status") == "returned",  1).otherwise(0)).alias("returned_count"),
            F.sum(F.col("quantity") * F.col("unit_price")).alias("gross_revenue"),
            F.sum(F.when(F.col("status").isin("delivered", "shipped"),
                         F.col("quantity") * F.col("unit_price")).otherwise(0.0)).alias("net_revenue"),
            F.sum("quantity").alias("total_items_sold"),
        )
        .withColumn("avg_order_value",
                    F.when(F.col("order_count") > 0,
                           F.col("gross_revenue") / F.col("order_count")).otherwise(0.0))
        .withColumn("_updated_at",   F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
    )


def build_gold_payments_summary(spark: SparkSession) -> DataFrame:
    p = spark.table(f"{CATALOG}.{SCHEMA}.silver_payments").filter("_is_deleted = false")
    return (
        p
        .withColumn("payment_month", F.date_format("payment_date", "yyyy-MM"))
        .groupBy("payment_month", "method")
        .agg(
            F.count("id").alias("transaction_count"),
            F.sum("amount").alias("total_amount"),
            F.sum(F.when(F.col("status") == "completed", F.col("amount")).otherwise(0.0)).alias("completed_amount"),
            F.sum(F.when(F.col("status") == "refunded",  F.col("amount")).otherwise(0.0)).alias("refunded_amount"),
            F.sum(F.when(F.col("status") == "pending",   F.col("amount")).otherwise(0.0)).alias("pending_amount"),
        )
        .withColumn("_updated_at",   F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
    )


def build_gold_returns_summary(spark: SparkSession) -> DataFrame:
    r = spark.table(f"{CATALOG}.{SCHEMA}.silver_returns").filter("_is_deleted = false")
    o = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")

    total_delivered = o.filter(F.col("status") == "delivered").count()

    return (
        r
        .withColumn("return_month", F.date_format("return_date", "yyyy-MM"))
        .groupBy("return_month", "reason", F.col("status").alias("return_status"))
        .agg(F.count("id").alias("return_count"))
        .withColumn("return_rate_pct",
                    F.when(F.lit(total_delivered) > 0,
                           F.col("return_count") / F.lit(float(total_delivered)) * 100.0
                    ).otherwise(0.0))
        .withColumn("_updated_at",   F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
    )


# ── Write helpers ─────────────────────────────────────────────────────────────

def refresh_gold_table(spark: SparkSession, name: str, df: DataFrame, batch_id: int) -> None:
    df.writeTo(f"{CATALOG}.{SCHEMA}.{name}").overwritePartitions()
    logger.info("Batch %d | %-28s | refreshed", batch_id, name)


def run_gold_refresh(spark: SparkSession, _df: DataFrame, batch_id: int) -> None:
    logger.info("Gold refresh triggered — batch %d", batch_id)
    try:
        refresh_gold_table(spark, "gold_customers",        build_gold_customers(spark),        batch_id)
        refresh_gold_table(spark, "gold_orders",           build_gold_orders(spark),           batch_id)
        refresh_gold_table(spark, "gold_sales_facts",      build_gold_sales_facts(spark),      batch_id)
        refresh_gold_table(spark, "gold_payments_summary", build_gold_payments_summary(spark), batch_id)
        refresh_gold_table(spark, "gold_returns_summary",  build_gold_returns_summary(spark),  batch_id)
    except Exception as exc:
        logger.error("Gold refresh batch %d error: %s", batch_id, exc, exc_info=True)
        # Re-raise so Spark marks the batch as failed rather than silently
        # continuing with stale Gold tables and no visible signal.
        raise


def main() -> None:
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    create_gold_tables(spark)

    # Heartbeat stream: silver_orders drives the 5-min trigger cycle
    heartbeat = (
        spark.readStream
        .format("iceberg")
        .option("stream-from-timestamp", "0")
        .load(f"{CATALOG}.{SCHEMA}.silver_orders")
    )

    query = (
        heartbeat.writeStream
        .foreachBatch(lambda df, bid: run_gold_refresh(spark, df, bid))
        .option("checkpointLocation", "s3a://warehouse/checkpoints/gold/main")
        .trigger(processingTime="5 minutes")
        .start()
    )

    logger.info("Gold aggregation stream running — refreshes every 5 minutes.")
    query.awaitTermination()


if __name__ == "__main__":
    main()
