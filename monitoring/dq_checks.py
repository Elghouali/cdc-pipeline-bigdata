#!/usr/bin/env python3
"""Data Quality checks for the CDC pipeline Gold layer.

Runs after each Gold refresh. Performs assertions against Trino-served
Iceberg tables, detects row-count regressions, records results into the
Postgres ``pipeline_alerts`` table (read by the CDC API), and exits with
code 0 (all checks passed) or 1 (one or more checks failed).

Environment variables:
  TRINO_HOST        default: trino
  TRINO_PORT        default: 8080
  TRINO_USER        default: dq-checks
  TRINO_CATALOG     default: iceberg
  TRINO_SCHEMA      default: default
  POSTGRES_HOST     default: postgres
  POSTGRES_PORT     default: 5432
  POSTGRES_DB       default: ecommerce
  POSTGRES_USER     default: postgres
  POSTGRES_PASSWORD default: postgres
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import trino
except ImportError:  # pragma: no cover
    print("ERROR: 'trino' package is required. Install with: pip install trino")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:  # pragma: no cover
    print("ERROR: 'psycopg2-binary' package is required. "
          "Install with: pip install psycopg2-binary")
    sys.exit(1)


STATE_FILE = Path(__file__).resolve().parent / "dq_state.json"
REGRESSION_THRESHOLD = 0.20  # alert if a count drops by more than 20%


# ─────────────────────────────────────────────────────────────────────
#  Connection helpers
# ─────────────────────────────────────────────────────────────────────
def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def trino_connection() -> "trino.dbapi.Connection":
    return trino.dbapi.connect(
        host=_env("TRINO_HOST", "trino"),
        port=int(_env("TRINO_PORT", "8080")),
        user=_env("TRINO_USER", "dq-checks"),
        catalog=_env("TRINO_CATALOG", "iceberg"),
        schema=_env("TRINO_SCHEMA", "default"),
    )


def postgres_connection():
    return psycopg2.connect(
        host=_env("POSTGRES_HOST", "postgres"),
        port=int(_env("POSTGRES_PORT", "5432")),
        dbname=_env("POSTGRES_DB", "ecommerce"),
        user=_env("POSTGRES_USER", "postgres"),
        password=_env("POSTGRES_PASSWORD", "postgres"),
    )


def scalar_query(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


# ─────────────────────────────────────────────────────────────────────
#  State persistence (row-count history for regression detection)
# ─────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARNING: could not read state file ({exc}); treating as empty.")
        return {}


def save_state(state: dict) -> None:
    try:
        with STATE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
    except OSError as exc:
        print(f"WARNING: could not write state file ({exc}).")


# ─────────────────────────────────────────────────────────────────────
#  Alert recording
# ─────────────────────────────────────────────────────────────────────
def record_alert(title: str, severity: str, details: dict) -> None:
    """Insert a row into the pipeline_alerts table read by the CDC API."""
    try:
        conn = postgres_connection()
    except Exception as exc:  # noqa: BLE001 - surface any connection failure
        print(f"WARNING: cannot record alert in Postgres ({exc}).")
        return
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_alerts (title, severity, details, fired_at)
                VALUES (%s, %s, %s, %s)
                """,
                (title, severity, Json(details), datetime.now(timezone.utc)),
            )
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to insert alert ({exc}).")
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────
#  Checks
# ─────────────────────────────────────────────────────────────────────
def run_checks() -> tuple[list[dict], dict]:
    """Execute all DQ assertions. Returns (results, new_state)."""
    catalog = _env("TRINO_CATALOG", "iceberg")
    schema = _env("TRINO_SCHEMA", "default")
    results: list[dict] = []
    new_state: dict = {}

    conn = trino_connection()
    try:
        cur = conn.cursor()

        # Check 1: no NULL customer_id in silver_customers
        null_ids = scalar_query(
            cur,
            f"SELECT COUNT(*) FROM {catalog}.{schema}.silver_customers "
            f"WHERE customer_id IS NULL",
        )
        results.append({
            "name": "silver_customers_no_null_id",
            "passed": null_ids == 0,
            "severity": "critical",
            "message": (
                f"silver_customers has {null_ids} rows with NULL customer_id "
                f"(expected 0)."
            ),
        })

        # Check 2: gold_customers is non-empty
        gold_count = scalar_query(
            cur, f"SELECT COUNT(*) FROM {catalog}.{schema}.gold_customers")
        results.append({
            "name": "gold_customers_non_empty",
            "passed": gold_count > 0,
            "severity": "critical",
            "message": (
                f"gold_customers has {gold_count} rows (expected > 0)."
            ),
        })

        # Check 3 + 4: row-count regression vs previous run
        silver_count = scalar_query(
            cur, f"SELECT COUNT(*) FROM {catalog}.{schema}.silver_customers")
        new_state = {
            "silver_customers_count": silver_count,
            "gold_customers_count": gold_count,
            "last_run": datetime.now(timezone.utc).isoformat(),
        }

        previous = load_state()
        for table, current in (
            ("silver_customers", silver_count),
            ("gold_customers", gold_count),
        ):
            prev = previous.get(f"{table}_count")
            if prev is None or prev == 0:
                results.append({
                    "name": f"{table}_regression",
                    "passed": True,
                    "severity": "warning",
                    "message": (
                        f"{table}: no usable baseline "
                        f"(prev={prev}); recorded current={current}."
                    ),
                })
                continue
            drop_ratio = (prev - current) / prev
            passed = drop_ratio <= REGRESSION_THRESHOLD
            results.append({
                "name": f"{table}_regression",
                "passed": passed,
                "severity": "warning",
                "message": (
                    f"{table} row count {prev} -> {current} "
                    f"({drop_ratio:+.1%} change; "
                    f"threshold {REGRESSION_THRESHOLD:.0%} drop)."
                ),
            })

        cur.close()
    finally:
        conn.close()

    return results, new_state


# ─────────────────────────────────────────────────────────────────────
#  Entrypoint
# ─────────────────────────────────────────────────────────────────────
def main() -> int:
    print(f"[dq_checks] starting at {datetime.now(timezone.utc).isoformat()}")

    try:
        results, new_state = run_checks()
    except Exception as exc:  # noqa: BLE001 - any failure is a DQ failure
        print(f"ERROR: data quality run failed: {exc}")
        record_alert(
            title="Data Quality run failed",
            severity="critical",
            details={"error": str(exc)},
        )
        return 1

    failures = [r for r in results if not r["passed"]]

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {result['name']}: {result['message']}")

    if failures:
        worst = "critical" if any(
            f["severity"] == "critical" for f in failures) else "warning"
        record_alert(
            title=f"Data Quality: {len(failures)} check(s) failed",
            severity=worst,
            details={"failures": failures, "total_checks": len(results)},
        )
    else:
        record_alert(
            title="Data Quality: all checks passed",
            severity="info",
            details={"total_checks": len(results)},
        )

    # Persist state only after a clean run so a bad run cannot poison the
    # baseline used for regression detection.
    if not failures:
        save_state(new_state)

    print(f"[dq_checks] finished: {len(results) - len(failures)} passed, "
          f"{len(failures)} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
