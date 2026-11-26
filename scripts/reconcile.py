#!/usr/bin/env python3
"""Read-only reconciliation of active key sets during a quiescent source window."""
import argparse
import json
import time

from cdc_smoke import postgres, trino_query

TABLES = ("customers", "products", "orders", "order_items", "payments", "returns")


def source_snapshot():
    return {
        table: postgres(
            f"SELECT count(*) || ':' || md5(coalesce(string_agg(id::text, ',' ORDER BY id), '')) FROM {table}"
        )
        for table in TABLES
    }


def silver_snapshot():
    return {
        table: trino_query(
            "SELECT cast(count(*) AS varchar) || ':' || "
            "lower(to_hex(md5(to_utf8(coalesce(array_join(array_agg(cast(id AS varchar) ORDER BY id), ','), ''))))) "
            f"FROM silver_{table} WHERE NOT _is_deleted"
        )
        for table in TABLES
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    deadline = time.monotonic() + args.timeout
    while True:
        before = source_snapshot()
        actual = silver_snapshot()
        after = source_snapshot()
        mismatches = [
            table for table in TABLES
            if before[table] != after[table] or before[table] != actual[table]
        ]
        if not mismatches:
            print(json.dumps({"status": "passed", "entities": list(TABLES)}))
            return 0
        if time.monotonic() >= deadline:
            print(json.dumps({"status": "failed", "mismatches": mismatches}))
            return 1
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
