#!/usr/bin/env python3
"""Read-only Iceberg maintenance inventory. Never rewrite or expire snapshots."""
import argparse
import json

from cdc_smoke import trino_query

ENTITIES = ("customers", "products", "orders", "order_items", "payments", "returns")
GOLD = ("customers", "orders", "sales_facts", "payments_summary", "returns_summary")
TABLES = tuple(f"bronze_{t}_cdc" for t in ENTITIES) + tuple(
    f"silver_{t}" for t in ENTITIES
) + tuple(f"gold_{t}" for t in GOLD)


def inventory(table):
    if table not in TABLES:
        raise ValueError("Unknown maintenance table")
    files = trino_query(
        "SELECT cast(count(*) AS varchar) || ',' || "
        "cast(coalesce(sum(file_size_in_bytes),0) AS varchar) || ',' || "
        "cast(count_if(file_size_in_bytes < 33554432) AS varchar) "
        f'FROM "{table}$files"'
    )
    snapshots = int(trino_query(f'SELECT count(*) FROM "{table}$snapshots"'))
    count, size, small = map(int, files.split(","))
    return {"table": table, "files": count, "bytes": size, "small_files": small,
            "snapshots": snapshots, "candidate": table.startswith("gold_") and small >= 5}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", choices=TABLES)
    args = parser.parse_args()
    rows = [inventory(t) for t in ([args.table] if args.table else TABLES)]
    print(json.dumps({"mode": "read_only", "tables": rows}, indent=2))


if __name__ == "__main__":
    main()
