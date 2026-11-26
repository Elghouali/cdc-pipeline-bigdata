#!/usr/bin/env python3
"""Require actual synthetic data and healthy upstream Spark pods in CI kind."""

import argparse
import json
import subprocess
import time

import kubernetes_cdc_smoke as kube

LAYERS = ("bronze", "silver", "gold")
TABLES = ("customers", "products", "orders", "order_items", "payments", "returns")
GOLD = ("customers", "orders", "sales_facts", "payments_summary", "returns_summary")


def check_pods(layer):
    ready = True
    for current in LAYERS[: LAYERS.index(layer) + 1]:
        raw = subprocess.run(
            ["kubectl", "-n", kube.NAMESPACE, "get", "pods", "-l",
             f"app.kubernetes.io/component=spark-{current}", "-o", "json"],
            capture_output=True, text=True, check=True, timeout=20,
        )
        pods = json.loads(raw.stdout)["items"]
        if len(pods) != 1:
            ready = False
            continue
        pod = pods[0]
        statuses = pod.get("status", {}).get("containerStatuses", [])
        if any(s.get("restartCount", 0) >= 3 for s in statuses):
            raise RuntimeError(f"Spark {current} restarted at least three times")
        if pod["metadata"].get("deletionTimestamp"):
            ready = False
        if not statuses or not all(s.get("ready") for s in statuses):
            ready = False
    return ready


def stage_sql(layer, customer_id):
    names = (
        [f"bronze_{t}_cdc" for t in TABLES] if layer == "bronze"
        else [f"silver_{t}" for t in TABLES] if layer == "silver"
        else [f"gold_{t}" for t in GOLD]
    )
    quoted = ", ".join(f"'{name}'" for name in names)
    tables = (
        "SELECT count(*) FROM information_schema.tables "
        f"WHERE table_schema='analytics' AND table_name IN ({quoted})"
    )
    if layer == "bronze":
        data = (
            "SELECT count(*) FROM bronze_customers_cdc WHERE op IN ('r','c') "
            "AND try_cast(json_extract_scalar(after_payload, '$.id') AS bigint) = "
            f"{customer_id}"
        )
    elif layer == "silver":
        data = (
            "SELECT count(*) FROM silver_customers WHERE NOT _is_deleted "
            f"AND id={customer_id}"
        )
    else:
        data = (
            "SELECT count(*) FROM gold_customers WHERE snapshot_date=current_date "
            f"AND customer_id={customer_id}"
        )
    return tables, len(names), data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layer", choices=LAYERS)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")

    customer_id = int(kube.postgres(
        "SELECT id FROM customers WHERE email='initial-fixture@example.invalid'"
    ))
    tables_sql, table_count, data_sql = stage_sql(args.layer, customer_id)
    deadline = time.monotonic() + args.timeout
    last = "no observations"
    while time.monotonic() < deadline:
        try:
            ready = check_pods(args.layer)
            count = int(kube.trino_query(tables_sql, timeout=25))
            records = int(kube.trino_query(data_sql, timeout=25)) if count == table_count else 0
            last = f"pods_ready={ready} tables={count}/{table_count} initial_records={records}"
            if ready and count == table_count and records == 1:
                print(f"PASS {args.layer}: {last}", flush=True)
                return
        except (subprocess.SubprocessError, ValueError, OSError) as exc:
            last = type(exc).__name__
        print(f"Waiting for {args.layer}: {last}", flush=True)
        time.sleep(10)
    raise TimeoutError(f"{args.layer} did not become ready: {last}")


if __name__ == "__main__":
    main()
