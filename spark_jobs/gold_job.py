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
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gold_job")

CATALOG = "iceberg"
SCHEMA = "analytics"
MONEY_COLUMNS = {
    "gold_customers": ["total_spent", "avg_order_value"],
    "gold_orders": ["order_total"],
    "gold_sales_facts": ["gross_revenue", "net_revenue", "avg_order_value"],
    "gold_payments_summary": [
        "total_amount",
        "completed_amount",
        "refunded_amount",
        "pending_amount",
    ],
}


def get_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("cdc-gold-aggregation")
        .config("spark.sql.catalog.iceberg.cache-enabled", "false")
        .getOrCreate()
    )


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
        total_spent      DECIMAL(28,2),
        avg_order_value  DECIMAL(28,2),
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
        order_total      DECIMAL(28,2),
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
        gross_revenue    DECIMAL(28,2),
        net_revenue      DECIMAL(28,2),
        total_items_sold BIGINT,
        avg_order_value  DECIMAL(28,2),
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
        total_amount      DECIMAL(28,2),
        completed_amount  DECIMAL(28,2),
        refunded_amount   DECIMAL(28,2),
        pending_amount    DECIMAL(28,2),
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

    for table, columns in MONEY_COLUMNS.items():
        schema = spark.table(f"{CATALOG}.{SCHEMA}.{table}").schema
        for column in columns:
            if schema[column].dataType.simpleString() != "decimal(28,2)":
                raise RuntimeError(
                    f"{table}.{column} requires explicit decimal migration"
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
        p.filter(F.col("status") == "completed")
        .join(
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
            F.coalesce(pay_agg.total_spent, F.lit(0).cast("decimal(28,2)")).alias(
                "total_spent"
            ),
            # avg_order_value = total_spent / total_orders, not AVG(payment.amount):
            # one order can span multiple payments so AVG(amount) would be wrong.
            F.when(
                order_agg.total_orders > 0,
                F.coalesce(pay_agg.total_spent, F.lit(0).cast("decimal(28,2)"))
                / order_agg.total_orders,
            )
            .otherwise(F.lit(0).cast("decimal(28,2)"))
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

    # Stable single payment descriptor per order; prefer completed payments,
    # then the latest date and source primary key.
    ranking = Window.partitionBy("order_id").orderBy(
        (F.col("status") == "completed").desc(),
        F.col("payment_date").desc(),
        F.col("id").desc(),
    )
    p = p.withColumn("_rank", F.row_number().over(ranking)).filter("_rank = 1")
    r = r.filter(F.col("status").isin("approved", "completed"))

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
            F.coalesce("order_total", F.lit(0).cast("decimal(28,2)")).alias(
                "order_total"
            ),
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
            "inner",
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
                ).otherwise(F.lit(0).cast("decimal(28,2)"))
            ).alias("net_revenue"),
            F.sum("quantity").alias("total_items_sold"),
        )
        .withColumn(
            "avg_order_value",
            F.when(
                F.col("order_count") > 0, F.col("gross_revenue") / F.col("order_count")
            ).otherwise(F.lit(0).cast("decimal(28,2)")),
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
                F.when(F.col("status") == "completed", F.col("amount")).otherwise(
                    F.lit(0).cast("decimal(28,2)")
                )
            ).alias("completed_amount"),
            F.sum(
                F.when(F.col("status") == "refunded", F.col("amount")).otherwise(
                    F.lit(0).cast("decimal(28,2)")
                )
            ).alias("refunded_amount"),
            F.sum(
                F.when(F.col("status") == "pending", F.col("amount")).otherwise(
                    F.lit(0).cast("decimal(28,2)")
                )
            ).alias("pending_amount"),
        )
        .withColumn("_updated_at", F.current_timestamp())
        .withColumn("snapshot_date", F.current_date())
    )


def build_gold_returns_summary(spark: SparkSession) -> DataFrame:
    r = spark.table(f"{CATALOG}.{SCHEMA}.silver_returns").filter("_is_deleted = false")
    o = spark.table(f"{CATALOG}.{SCHEMA}.silver_orders").filter("_is_deleted = false")

    # Cohort = order month, eligible orders are delivered or returned.
    # Each reason/status rate is distinct eligible orders in that cohort;
    # categories can overlap and are not additive.
    eligible = o.filter(F.col("status").isin("delivered", "returned")).select(
        F.col("id").alias("oid"),
        F.date_format("order_date", "yyyy-MM").alias("return_month"),
    )
    denominator = eligible.groupBy("return_month").agg(
        F.countDistinct("oid").alias("eligible_count")
    )
    returns_agg = (
        r.join(eligible, r.order_id == eligible.oid, "inner")
        .groupBy("return_month", "reason", F.col("status").alias("return_status"))
        .agg(F.countDistinct("order_id").alias("return_count"))
    )
    return (
        returns_agg.join(denominator, "return_month", "inner")
        .withColumn(
            "return_rate_pct",
            F.when(
                F.col("return_status").isin("approved", "completed"),
                F.col("return_count") / F.col("eligible_count") * 100.0,
            ).otherwise(F.lit(0).cast("decimal(28,2)")),
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
    for column in MONEY_COLUMNS.get(name, []):
        df = df.withColumn(column, F.col(column).cast("decimal(28,2)"))
    df.withColumn("snapshot_date", F.lit(snapshot_date)).writeTo(
        f"{CATALOG}.{SCHEMA}.{name}"
    ).overwrite(F.col("snapshot_date") == F.lit(snapshot_date))
    logger.info("Batch %d | %-28s | refreshed", batch_id, name)


def run_gold_refresh(spark: SparkSession, batch_id: int) -> None:
    # Freeze one date across all five outputs, including midnight refreshes.
    snapshot_date = spark.sql("SELECT current_date() AS day").first().day
    logger.info("Gold refresh triggered — batch %d", batch_id)
    try:
        # Silver writes from another Spark application. Invalidate Spark SQL
        # metadata before building each new set of batch DataFrames.
        for table in (
            "customers",
            "products",
            "orders",
            "order_items",
            "payments",
            "returns",
        ):
            spark.catalog.refreshTable(f"{CATALOG}.{SCHEMA}.silver_{table}")
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


def publish_refresh_timestamp() -> None:
    """Record completion of all five Gold writes, even on idle source days."""
    runtime = Path("/var/lib/cdc-runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    target = runtime / "gold-refresh"
    temporary = runtime / "gold-refresh.tmp"
    temporary.write_text(str(time.time()), encoding="utf-8")
    temporary.chmod(0o644)
    temporary.replace(target)


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
            publish_refresh_timestamp()
            batch_id += 1
            time.sleep(max(0, args.interval_seconds - (time.monotonic() - started)))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
