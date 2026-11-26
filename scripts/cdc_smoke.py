#!/usr/bin/env python3
"""Exercise real PostgreSQL -> Bronze -> Silver (optionally Gold) CDC.

Run from the repository root against an isolated, already-started stack.
Uses only the Python standard library and the Docker Compose CLI.
"""
import argparse
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

COMPOSE = ["docker", "compose", "exec", "-T"]


def command(args, timeout=30):
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=True
    )
    return result.stdout.strip()


def postgres(sql):
    # The SQL is passed as a separate argument, never interpolated by the shell.
    return command(COMPOSE + [
        "postgres", "sh", "-c",
        'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d ecommerce -c "$1"',
        "cdc-smoke", sql,
    ])


def trino_query(sql, timeout=30):
    return command(COMPOSE + [
        "trino", "trino", "--catalog", "iceberg", "--schema", "analytics",
        "--output-format", "TSV", "--execute", sql,
    ], timeout=timeout)


def trino_count(sql, timeout=30):
    return int(trino_query(sql, timeout))


def wait_for(label, sql, predicate, timeout, interval):
    started = time.monotonic()
    deadline = started + timeout
    last = "no observation"
    while time.monotonic() < deadline:
        try:
            count = trino_count(sql, timeout=min(30, max(0.1, deadline - time.monotonic())))
            last = str(count)
            if predicate(count):
                elapsed = round(time.monotonic() - started, 3)
                print(f"PASS {label}: {elapsed}s", flush=True)
                return {"check": label, "status": "passed", "seconds": elapsed, "count": count}
        except (subprocess.SubprocessError, ValueError) as exc:
            last = type(exc).__name__
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"{label}: not satisfied within {timeout}s (last observation: {last})")


def bronze_sql(customer_id, op):
    if op not in {"c", "u", "d"}:
        raise ValueError("Unsupported operation")
    return (
        "SELECT count(*) FROM bronze_customers_cdc "
        f"WHERE op = '{op}' AND "
        "try_cast(json_extract_scalar(coalesce(after_payload, before_payload), '$.id') "
        f"AS bigint) = {int(customer_id)}"
    )


def silver_sql(customer_id, city=None, deleted=False):
    # Count ALL matching PK rows only when exactly one row exists with the expected state.
    if city not in {None, "Casablanca", "Rabat"}:
        raise ValueError("Unsupported test city")
    condition = "_is_deleted = true" if deleted else f"_is_deleted = false AND city = '{city}'"
    return (
        "SELECT CASE WHEN count(*) = 1 AND count_if("
        f"{condition}) = 1 THEN 1 ELSE 0 END "
        f"FROM silver_customers WHERE id = {int(customer_id)}"
    )


def gold_sql(customer_id, city=None):
    if city not in {None, "Casablanca", "Rabat"}:
        raise ValueError("Unsupported test city")
    where = f"customer_id = {int(customer_id)} AND snapshot_date = current_date"
    if city is None:
        return f"SELECT count(*) FROM gold_customers WHERE {where}"
    return (
        f"SELECT CASE WHEN count(*) = 1 AND count_if(city = '{city}' AND total_orders = 0 "
        "AND total_spent = 0 AND avg_order_value = 0) = 1 "
        f"THEN 1 ELSE 0 END FROM gold_customers WHERE {where}"
    )


def run(args):
    email = f"cdc-smoke-{uuid.uuid4().hex}@example.invalid"
    report = {"started_at": datetime.now(timezone.utc).isoformat(),
              "scope": "bronze-silver-gold" if args.gold else "bronze-silver",
              "status": "failed", "checks": []}
    customer_id = None
    current_check = "readiness"

    def observe(label, sql, predicate, timeout=None):
        nonlocal current_check
        current_check = label
        report["checks"].append(wait_for(
            label, sql, predicate, timeout or args.timeout, args.interval
        ))

    try:
        for table in ("bronze_customers_cdc", "silver_customers"):
            observe(f"ready:{table}", f"SELECT count(*) FROM {table}", lambda n: n >= 0)
        if args.gold:
            observe("ready:gold_customers",
                    "SELECT count(*) FROM gold_customers WHERE snapshot_date = current_date",
                    lambda n: n > 0, args.gold_timeout)

        current_check = "source:insert"
        customer_id = int(postgres(
            "INSERT INTO customers(name,email,city,segment) "
            f"VALUES ('CDC smoke test','{email}','Casablanca','B2C') RETURNING id;"
        ))
        report["customer_id"] = customer_id
        for op, city in (("c", "Casablanca"), ("u", "Rabat"), ("d", None)):
            started = time.monotonic()
            if op == "u":
                current_check = "source:update"
                postgres(f"UPDATE customers SET city='Rabat' WHERE id={customer_id};")
            elif op == "d":
                current_check = "source:delete"
                postgres(f"DELETE FROM customers WHERE id={customer_id};")
            observe(f"bronze:{op}", bronze_sql(customer_id, op), lambda n: n >= 1)
            report["checks"][-1]["observed_since_stage_start_seconds"] = round(time.monotonic() - started, 3)
            observe(f"silver:{op}", silver_sql(customer_id, city, op == "d"), lambda n: n == 1)
            report["checks"][-1]["observed_since_stage_start_seconds"] = round(time.monotonic() - started, 3)
            if args.gold:
                expected = 0 if op == "d" else 1
                observe(f"gold:{op}", gold_sql(customer_id, city),
                        lambda n: n == expected, args.gold_timeout)
                report["checks"][-1]["observed_since_stage_start_seconds"] = round(time.monotonic() - started, 3)
        report["status"] = "passed"
    except (subprocess.SubprocessError, ValueError, TimeoutError, OSError) as exc:
        report["failed_check"] = current_check
        report["error"] = str(exc) if isinstance(exc, TimeoutError) else type(exc).__name__
        print(f"FAIL {current_check}: {report['error']}", flush=True)
        if args.gold and current_check.startswith('gold:') and customer_id is not None:
            # Capture only the synthetic fixture's non-identifying fields before cleanup.
            diagnostics = {}
            for name, sql in (
                ('silver', f'SELECT id, city, _is_deleted FROM silver_customers WHERE id = {customer_id}'),
                ('gold', f'SELECT customer_id, city, total_orders, total_spent, avg_order_value, snapshot_date FROM gold_customers WHERE customer_id = {customer_id} AND snapshot_date = current_date'),
            ):
                try:
                    diagnostics[name] = trino_query(sql, timeout=20)
                except (subprocess.SubprocessError, OSError) as diag_exc:
                    diagnostics[name] = type(diag_exc).__name__
            report['gold_failure_diagnostics'] = diagnostics
            print(f'Gold fixture diagnostics: {json.dumps(diagnostics)}', flush=True)
    finally:
        try:
            # Unique fixture only, even when the source insert response was lost.
            postgres(f"DELETE FROM customers WHERE email='{email}';")
            report["source_cleanup"] = "passed"
        except (subprocess.SubprocessError, OSError) as exc:
            report["source_cleanup"] = type(exc).__name__
            report["status"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {output}", flush=True)
    return 0 if report["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=300, help="Per Bronze/Silver check (seconds)")
    parser.add_argument("--gold", action="store_true", help="Also verify Gold snapshot")
    parser.add_argument("--gold-timeout", type=float, default=600)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--output", default="artifacts/cdc-smoke.json")
    args = parser.parse_args()
    if min(args.timeout, args.gold_timeout, args.interval) <= 0:
        parser.error("Timeouts and interval must be positive")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
