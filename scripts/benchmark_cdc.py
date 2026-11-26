#!/usr/bin/env python3
"""Bounded isolated CDC burst benchmark; reports observation bounds, not per-row latency."""
import argparse
import json
import time
import uuid
from pathlib import Path

from cdc_smoke import postgres, wait_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--output", default="artifacts/cdc-benchmark.json")
    args = parser.parse_args()
    if not 1 <= args.rows <= 10000:
        parser.error("rows must be between 1 and 10000")
    token = "bench-" + uuid.uuid4().hex
    predicate = f"email LIKE '{token}-%@example.invalid'"
    prefix = f"{token}-%@example.invalid"
    result = {"rows": args.rows, "status": "failed", "measurements": []}
    started = time.monotonic()
    try:
        postgres(
            "INSERT INTO customers(name,email,city,segment) "
            f"SELECT 'Benchmark','{token}-' || n || '@example.invalid','Rabat','B2C' "
            f"FROM generate_series(1,{args.rows}) n"
        )
        commit = time.monotonic()
        result["source_transaction_seconds"] = round(commit - started, 3)
        result["source_rows_per_second"] = round(args.rows / max(commit - started, 0.001), 3)
        queries = (
            ("bronze", "SELECT count(*) FROM bronze_customers_cdc WHERE op='c' "
             f"AND json_extract_scalar(after_payload, '$.email') LIKE '{prefix}'"),
            ("silver", f"SELECT count(*) FROM silver_customers WHERE NOT _is_deleted AND email LIKE '{prefix}'"),
            ("gold", f"SELECT count(*) FROM gold_customers WHERE snapshot_date=current_date AND name='Benchmark' AND customer_id IN (SELECT id FROM silver_customers WHERE NOT _is_deleted AND email LIKE '{prefix}')"),
        )
        for layer, sql in queries:
            record = wait_for("benchmark:" + layer, sql, lambda n: n == args.rows, 300, 3)
            record["observed_after_source_commit_seconds"] = round(time.monotonic() - commit, 3)
            result["measurements"].append(record)
        result["status"] = "passed"
    finally:
        postgres(f"DELETE FROM customers WHERE {predicate}")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
