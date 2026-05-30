-- ─────────────────────────────────────────────────────────────────────────────
--  trino_queries.sql
--  Run against: Trino 435  |  catalog: iceberg  |  schema: analytics
--
--  KPI 1  — CDC event counts by table
--  KPI 2  — Operation type breakdown (c/u/d/r) per table
--  KPI 3  — Source-to-analytics latency (WAL timestamp -> Bronze ingestion)
--  KPI 4  — Order status evolution (weekly)
--  KPI 5  — Total sales by period and channel
--  KPI 6  — Payment method mix by month
--  KPI 7  — Cancellation and return rates (monthly)
--  KPI 8  — Revenue by customer segment and product category
--  Bonus  — Top 10 customers by lifetime value
--  Bonus  — Return reason breakdown
-- ─────────────────────────────────────────────────────────────────────────────

USE iceberg.analytics;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 1 — CDC event counts by table
--  How many raw CDC rows have landed in Bronze for each entity.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    source_table,
    COUNT(*)                                   AS total_events,
    COUNT(*) FILTER (WHERE op = 'c')           AS inserts,
    COUNT(*) FILTER (WHERE op = 'u')           AS updates,
    COUNT(*) FILTER (WHERE op = 'd')           AS deletes,
    COUNT(*) FILTER (WHERE op = 'r')           AS snapshots,
    MIN(ingestion_timestamp)                   AS first_event_at,
    MAX(ingestion_timestamp)                   AS last_event_at
FROM (
    SELECT op, source_table, ingestion_timestamp FROM bronze_customers_cdc
    UNION ALL
    SELECT op, source_table, ingestion_timestamp FROM bronze_products_cdc
    UNION ALL
    SELECT op, source_table, ingestion_timestamp FROM bronze_orders_cdc
    UNION ALL
    SELECT op, source_table, ingestion_timestamp FROM bronze_order_items_cdc
    UNION ALL
    SELECT op, source_table, ingestion_timestamp FROM bronze_payments_cdc
    UNION ALL
    SELECT op, source_table, ingestion_timestamp FROM bronze_returns_cdc
) b
GROUP BY source_table
ORDER BY total_events DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 2 — Operation type breakdown per table (with percentage)
-- ─────────────────────────────────────────────────────────────────────────────
WITH raw AS (
    SELECT op, source_table FROM bronze_customers_cdc
    UNION ALL SELECT op, source_table FROM bronze_products_cdc
    UNION ALL SELECT op, source_table FROM bronze_orders_cdc
    UNION ALL SELECT op, source_table FROM bronze_order_items_cdc
    UNION ALL SELECT op, source_table FROM bronze_payments_cdc
    UNION ALL SELECT op, source_table FROM bronze_returns_cdc
),
counts AS (
    SELECT source_table, op, COUNT(*) AS cnt
    FROM raw GROUP BY source_table, op
),
totals AS (
    SELECT source_table, SUM(cnt) AS total FROM counts GROUP BY source_table
)
SELECT
    c.source_table,
    c.op,
    c.cnt                                          AS event_count,
    ROUND(c.cnt * 100.0 / t.total, 2)             AS pct_of_table
FROM counts c
JOIN totals t USING (source_table)
ORDER BY c.source_table, c.op;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 3 — Source-to-analytics latency
--  Measures WAL timestamp (source_ts_ms) vs. Bronze ingestion_timestamp.
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    source_table,
    COUNT(*)                                                             AS events,
    ROUND(AVG(
        (to_unixtime(ingestion_timestamp) * 1000.0 - source_ts_ms) / 1000.0
    ), 2)                                                                AS avg_latency_sec,
    ROUND(MIN(
        (to_unixtime(ingestion_timestamp) * 1000.0 - source_ts_ms) / 1000.0
    ), 2)                                                                AS min_latency_sec,
    ROUND(MAX(
        (to_unixtime(ingestion_timestamp) * 1000.0 - source_ts_ms) / 1000.0
    ), 2)                                                                AS max_latency_sec,
    ROUND(approx_percentile(
        (to_unixtime(ingestion_timestamp) * 1000.0 - source_ts_ms) / 1000.0, 0.95
    ), 2)                                                                AS p95_latency_sec
FROM (
    SELECT source_table, source_ts_ms, ingestion_timestamp
    FROM bronze_customers_cdc    WHERE source_ts_ms IS NOT NULL
    UNION ALL
    SELECT source_table, source_ts_ms, ingestion_timestamp
    FROM bronze_products_cdc     WHERE source_ts_ms IS NOT NULL
    UNION ALL
    SELECT source_table, source_ts_ms, ingestion_timestamp
    FROM bronze_orders_cdc       WHERE source_ts_ms IS NOT NULL
    UNION ALL
    SELECT source_table, source_ts_ms, ingestion_timestamp
    FROM bronze_order_items_cdc  WHERE source_ts_ms IS NOT NULL
    UNION ALL
    SELECT source_table, source_ts_ms, ingestion_timestamp
    FROM bronze_payments_cdc     WHERE source_ts_ms IS NOT NULL
    UNION ALL
    SELECT source_table, source_ts_ms, ingestion_timestamp
    FROM bronze_returns_cdc      WHERE source_ts_ms IS NOT NULL
) lat
GROUP BY source_table
ORDER BY avg_latency_sec DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 4 — Order status evolution (weekly view)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    date_trunc('week', order_date)               AS week_start,
    status,
    COUNT(*)                                     AS order_count,
    ROUND(SUM(order_total), 2)                   AS week_revenue
FROM gold_orders
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_orders)
GROUP BY 1, 2
ORDER BY 1 DESC, order_count DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 5 — Total sales by period and channel
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    date_format(sale_date, '%Y-%m')                                       AS sale_month,
    channel,
    SUM(order_count)                                                      AS total_orders,
    ROUND(SUM(gross_revenue), 2)                                          AS gross_revenue,
    ROUND(SUM(net_revenue),   2)                                          AS net_revenue,
    ROUND(SUM(gross_revenue) - SUM(net_revenue), 2)                       AS lost_revenue,
    SUM(total_items_sold)                                                 AS items_sold,
    -- Weighted average: total revenue / total orders avoids the statistical
    -- error of averaging pre-aggregated averages (AVG of AVGs ignores volume).
    ROUND(SUM(gross_revenue) / NULLIF(SUM(order_count), 0), 2)           AS avg_basket
FROM gold_sales_facts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_sales_facts)
GROUP BY 1, 2
ORDER BY 1 DESC, gross_revenue DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 6 — Payment method mix by month
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    payment_month,
    method,
    transaction_count,
    ROUND(total_amount,     2)  AS total_collected,
    ROUND(completed_amount, 2)  AS completed,
    ROUND(refunded_amount,  2)  AS refunded,
    ROUND(pending_amount,   2)  AS pending,
    ROUND(refunded_amount * 100.0 / NULLIF(total_amount, 0), 2)  AS refund_rate_pct
FROM gold_payments_summary
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_payments_summary)
ORDER BY payment_month DESC, total_amount DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 7 — Cancellation and return rates (monthly)
-- ─────────────────────────────────────────────────────────────────────────────
WITH monthly AS (
    SELECT
        date_format(order_date, '%Y-%m')             AS order_month,
        COUNT(*)                                      AS total_orders,
        COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
        COUNT(*) FILTER (WHERE status = 'returned')  AS returned,
        COUNT(*) FILTER (WHERE status = 'delivered') AS delivered
    FROM gold_orders
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_orders)
    GROUP BY 1
)
SELECT
    order_month,
    total_orders,
    cancelled,
    returned,
    delivered,
    ROUND(cancelled * 100.0 / NULLIF(total_orders, 0), 2) AS cancellation_rate_pct,
    ROUND(returned  * 100.0 / NULLIF(delivered,    0), 2) AS return_rate_pct
FROM monthly
ORDER BY order_month DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  KPI 8 — Revenue breakdown by customer segment and product category
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    customer_segment,
    product_category,
    SUM(order_count)                                                    AS total_orders,
    ROUND(SUM(gross_revenue), 2)                                        AS gross_revenue,
    ROUND(SUM(net_revenue),   2)                                        AS net_revenue,
    SUM(total_items_sold)                                               AS items_sold,
    ROUND(SUM(gross_revenue) / NULLIF(SUM(order_count), 0), 2)         AS avg_basket
FROM gold_sales_facts
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_sales_facts)
GROUP BY 1, 2
ORDER BY gross_revenue DESC;


-- ─────────────────────────────────────────────────────────────────────────────
--  Bonus — Top 10 customers by lifetime value
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    customer_id,
    name,
    city,
    segment,
    total_orders,
    delivered_orders,
    ROUND(total_spent,     2) AS lifetime_value,
    ROUND(avg_order_value, 2) AS avg_basket,
    last_order_date
FROM gold_customers
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_customers)
ORDER BY lifetime_value DESC
LIMIT 10;


-- ─────────────────────────────────────────────────────────────────────────────
--  Bonus — Return reason breakdown
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    return_month,
    reason,
    return_status,
    return_count,
    ROUND(return_rate_pct, 3) AS return_rate_pct
FROM gold_returns_summary
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_returns_summary)
ORDER BY return_month DESC, return_count DESC;
