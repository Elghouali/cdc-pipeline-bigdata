"""
gold_job.py — Medallion Layer: Gold

Reads Silver Iceberg tables, applies business aggregations, and upserts
Gold fact/dimension tables via explicit daily partition overwrite.

Gold tables produced (iceberg.analytics.*):
  gold_customers        - customer 360: order count, total spend, last order
  gold_orders           - enriched order view joining customer + payment info
  gold_sales_facts      - daily KPIs by channel and customer segment
  gold_payments_summary - payment method breakdown by month
  gold_returns_summary  - return rate and reason breakdown by month

Partition column: snapshot_date DATE (today's date for all tables).
Schedule: periodic batch refresh (300 seconds by default), independent of order events.

Run:
  spark-submit --master spark://spark-master:7077 /opt/spark-apps/gold_job.py
"""

import argparse
import logging
import time
from datetime import date

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gold_job")

CATALOG = "iceberg"
SCHEMA = "analytics"


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

    spark.sql(
        _ddl(
            "gold_customers",
            """
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
    """,
        )
    )

    spark.sql(
        _ddl(
            "gold_orders",
            """
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
    """,
        )
    )

    spark.sql(
        _ddl(
            "gold_sales_facts",
            """
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
    """,
        )
    )

    spark.sql(
        _ddl(
            "gold_payments_summary",
            """
        payment_month     STRING,
        method            STRING,
        transaction_count BIGINT,
        total_amount      DOUBLE,
        completed_amount  DOUBLE,
        refunded_amount   DOUBLE,
        pending_amount    DOUBLE,
        _updated_at       TIMESTAMP
    """,
        )
    )

    spark.sql(
        _ddl(
            "gold_returns_summary",
            """
        return_month    STRING,
        reason          STRING,
        return_status   STRING,
        return_count    BIGINT,
        return_rate_pct DOUBLE,
        _updated_at     TIMESTAMP
    """,
        )
    )

    logger.info("All Gold tables ready.")


# ── Aggregation builders ──────────────────────────────────────────────────────


def build_gold_customers(spark: SparkSession) -> DataFrame:
    c = spark.table(f"{CATALOG}.{SCHEMA}.silver_customers").filter(
        "_is_deleted = false"
    )
    o = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")
    p = spark.table(f"{CATALOG}.{SCHEMA}.silver_payments").filter("_is_deleted = false")

    order_agg = o.groupBy("customer_id").agg(
        F.count("id").alias("total_orders"),
        F.sum(F.when(F.col("status") == "delivered", 1).otherwise(0)).alias(
            "delivered_orders"
        ),
        F.sum(F.when(F.col("status") == "cancelled", 1).otherwise(0)).alias(
            "cancelled_orders"
        ),
        F.sum(F.when(F.col("status") == "returned", 1).otherwise(0)).alias(
            "returned_orders"
        ),
        F.max("order_date").alias("last_order_date"),
        F.min("order_date").alias("first_order_date"),
    )

    pay_agg = (
        p.join(
            o.select(F.col("id").alias("oid"), "customer_id"),
            p.order_id == F.col("oid"),
        )
        .groupBy("customer_id")
        .agg(
            F.sum("amount").alias("total_spent"),
        )
    )

    return (
        c.join(order_agg, c.id == order_agg.customer_id, "left")
        .join(pay_agg, c.id == pay_agg.customer_id, "left")
        .select(
            c.id.alias("customer_id"),
            c.name,
            c.city,
            c.segment,
            F.coalesce(order_agg.total_orders, F.lit(0)).alias("total_orders"),
            F.coalesce(order_agg.delivered_orders, F.lit(0)).alias("delivered_orders"),
            F.coalesce(order_agg.cancelled_orders, F.lit(0)).alias("cancelled_orders"),
            F.coalesce(order_agg.returned_orders, F.lit(0)).alias("returned_orders"),
            F.coalesce(pay_agg.total_spent, F.lit(0.0)).alias("total_spent"),
            # avg_order_value = total_spent / total_orders, not AVG(payment.amount):
            # one order can span multiple payments so AVG(amount) would be wrong.
            F.when(
                order_agg.total_orders > 0,
                F.coalesce(pay_agg.total_spent, F.lit(0.0))
                / order_agg.total_orders.cast("double"),
            )
            .otherwise(0.0)
            .alias("avg_order_value"),
            order_agg.last_order_date,
            order_agg.first_order_date,
            F.current_timestamp().alias("_updated_at"),
            F.current_date().alias("snapshot_date"),
        )
    )


def build_gold_orders(spark: SparkSession) -> DataFrame:
    o = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")
    c = spark.table(f"{CATALOG}.{SCHEMA}.silver_customers").filter(
        "_is_deleted = false"
    )
    oi = spark.table(f"{CATALOG}.{SCHEMA}.silver_order_items").filter(
        "_is_deleted = false"
    )
    p = spark.table(f"{CATALOG}.{SCHEMA}.silver_payments").filter("_is_deleted = false")
    r = spark.table(f"{CATALOG}.{SCHEMA}.silver_returns").filter("_is_deleted = false")

    items = oi.groupBy("order_id").agg(
        F.sum(F.col("quantity") * F.col("unit_price")).alias("order_total"),
        F.sum("quantity").alias("item_count"),
    )

    return (
        o.join(
            c.select(F.col("id").alias("cid"), "name", "segment", "city"),
            o.customer_id == F.col("cid"),
            "left",
        )
        .join(items, o.id == items.order_id, "left")
        .join(
            p.select(
                F.col("order_id").alias("pid"),
                F.col("method").alias("pay_method"),
                F.col("status").alias("pay_status"),
            ),
            o.id == F.col("pid"),
            "left",
        )
        .join(
            r.select(F.col("order_id").alias("rid")).distinct(),
            o.id == F.col("rid"),
            "left",
        )
        .select(
            o.id.alias("order_id"),
            o.order_date,
            o.customer_id,
            F.col("name").alias("customer_name"),
            F.col("segment").alias("customer_segment"),
            F.col("city").alias("customer_city"),
            o.status,
            o.channel,
            F.coalesce("order_total", F.lit(0.0)).alias("order_total"),
            F.coalesce("item_count", F.lit(0)).alias("item_count"),
            F.col("pay_method").alias("payment_method"),
            F.col("pay_status").alias("payment_status"),
            F.col("rid").isNotNull().alias("has_return"),
            F.current_timestamp().alias("_updated_at"),
            F.current_date().alias("snapshot_date"),
        )
    )


def build_gold_sales_facts(spark: SparkSession) -> DataFrame:
    o = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")
    c = spark.table(f"{CATALOG}.{SCHEMA}.silver_customers").filter(
        "_is_deleted = false"
    )
    oi = spark.table(f"{CATALOG}.{SCHEMA}.silver_order_items").filter(
        "_is_deleted = false"
    )
    pr = spark.table(f"{CATALOG}.{SCHEMA}.silver_products").filter(
        "_is_deleted = false"
    )

    enriched = (
        oi.join(
            pr.select(F.col("id").alias("prid"), "category"),
            oi.product_id == F.col("prid"),
            "left",
        )
        .join(
            o.select(
                F.col("id").alias("oid"),
                "order_date",
                "customer_id",
                "status",
                "channel",
            ),
            oi.order_id == F.col("oid"),
            "left",
        )
        .join(
            c.select(F.col("id").alias("cid"), "segment"),
            F.col("customer_id") == F.col("cid"),
            "left",
        )
    )

    return (
        enriched.groupBy(
            F.col("order_date").alias("sale_date"),
            "channel",
            F.col("segment").alias("customer_segment"),
            F.col("category").alias("product_category"),
        )
        .agg(
            F.countDistinct(oi.order_id).alias("order_count"),
            # Count distinct order_ids per status — using SUM(WHEN) would count
            # item rows (one order with 3 items counts as 3, not 1).
            F.countDistinct(F.when(F.col("status") == "delivered", oi.order_id)).alias(
                "delivered_count"
            ),
            F.countDistinct(F.when(F.col("status") == "cancelled", oi.order_id)).alias(
                "cancelled_count"
            ),
            F.countDistinct(F.when(F.col("status") == "returned", oi.order_id)).alias(
                "returned_count"
            ),
            F.sum(F.col("quantity") * F.col("unit_price")).alias("gross_revenue"),
            F.sum(
                F.when(
                    F.col("status").isin("delivered", "shipped"),
                    F.col("quantity") * F.col("unit_price"),
                ).otherwise(0.0)
            ).alias("net_revenue"),
            F.sum("quantity").alias("total_items_sold"),
        )
        .withColumn(
            "avg_order_value",
            F.when(
                F.col("order_count") > 0, F.col("gross_revenue") / F.col("order_count")
            ).otherwise(0.0),
        )
        .withColumn("_updated_at", F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
    )


def build_gold_payments_summary(spark: SparkSession) -> DataFrame:
    p = spark.table(f"{CATALOG}.{SCHEMA}.silver_payments").filter("_is_deleted = false")
    return (
        p.withColumn("payment_month", F.date_format("payment_date", "yyyy-MM"))
        .groupBy("payment_month", "method")
        .agg(
            F.count("id").alias("transaction_count"),
            F.sum("amount").alias("total_amount"),
            F.sum(
                F.when(F.col("status") == "completed", F.col("amount")).otherwise(0.0)
            ).alias("completed_amount"),
            F.sum(
                F.when(F.col("status") == "refunded", F.col("amount")).otherwise(0.0)
            ).alias("refunded_amount"),
            F.sum(
                F.when(F.col("status") == "pending", F.col("amount")).otherwise(0.0)
            ).alias("pending_amount"),
        )
        .withColumn("_updated_at", F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
    )


def build_gold_returns_summary(spark: SparkSession) -> DataFrame:
    r = spark.table(f"{CATALOG}.{SCHEMA}.silver_returns").filter("_is_deleted = false")
    o = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")

    # Monthly delivered order counts — used as per-month denominator so that
    # return_rate_pct is meaningful (returns this month / delivered this month).
    # Using an all-time total would make the rate shrink every month regardless
    # of actual return behaviour.
    monthly_delivered = (
        o.filter(F.col("status") == "delivered")
        .withColumn("order_month", F.date_format("order_date", "yyyy-MM"))
        .groupBy("order_month")
        .agg(F.count("id").alias("delivered_count"))
    )

    returns_agg = (
        r.withColumn("return_month", F.date_format("return_date", "yyyy-MM"))
        .groupBy("return_month", "reason", F.col("status").alias("return_status"))
        .agg(F.count("id").alias("return_count"))
    )

    return (
        returns_agg.join(
            monthly_delivered,
            returns_agg.return_month == monthly_delivered.order_month,
            "left",
        )
        .withColumn(
            "return_rate_pct",
            F.when(
                F.col("delivered_count").isNotNull() & (F.col("delivered_count") > 0),
                F.col("return_count") / F.col("delivered_count") * 100.0,
            ).otherwise(0.0),
        )
        .withColumn("_updated_at", F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
        .select(
            "return_month",
            "reason",
            "return_status",
            "return_count",
            "return_rate_pct",
            "_updated_at",
            "snapshot_date",
        )
    )


# ── Write helpers ─────────────────────────────────────────────────────────────


def refresh_gold_table(
    name: str, df: DataFrame, batch_id: int, snapshot_date: date
) -> None:
    # Overwrite today's partition even if the new snapshot contains no rows.
    # Dynamic overwrite would leave stale data when a partition becomes empty.
    df.withColumn("snapshot_date", F.lit(snapshot_date)).writeTo(
        f"{CATALOG}.{SCHEMA}.{name}"
    ).overwrite(F.col("snapshot_date") == F.lit(snapshot_date))
    logger.info("Batch %d | %-28s | refreshed", batch_id, name)


def run_gold_refresh(spark: SparkSession, batch_id: int) -> None:
    # Freeze one date across all five outputs, including midnight refreshes.
    snapshot_date = spark.sql("SELECT current_date() AS day").first().day
    logger.info("Gold refresh triggered — batch %d", batch_id)
    try:
        refresh_gold_table(
            "gold_customers", build_gold_customers(spark), batch_id, snapshot_date
        )
        refresh_gold_table(
            "gold_orders", build_gold_orders(spark), batch_id, snapshot_date
        )
        refresh_gold_table(
            "gold_sales_facts", build_gold_sales_facts(spark), batch_id, snapshot_date
        )
        refresh_gold_table(
            "gold_payments_summary",
            build_gold_payments_summary(spark),
            batch_id,
            snapshot_date,
        )
        refresh_gold_table(
            "gold_returns_summary",
            build_gold_returns_summary(spark),
            batch_id,
            snapshot_date,
        )
    except Exception as exc:
        logger.exception("Gold refresh batch %d error: %s", batch_id, exc)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-seconds", type=int, default=300)
    args = parser.parse_args()
    if args.interval_seconds <= 0:
        parser.error("Refresh interval must be positive")

    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")
    try:
        create_gold_tables(spark)
        batch_id = 0
        # Recompute the daily snapshot on a timer, not on silver_orders.
        # Customer/payment-only changes must trigger refreshes as well.
        while True:
            started = time.monotonic()
            run_gold_refresh(spark, batch_id)
            batch_id += 1
            time.sleep(max(0, args.interval_seconds - (time.monotonic() - started)))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
