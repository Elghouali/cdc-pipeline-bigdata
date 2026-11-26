#!/usr/bin/env python3
"""Reuse the live CDC acceptance checks using kubectl instead of Compose.

Only invoke against an isolated namespace with synthetic data.
"""
import cdc_smoke


NAMESPACE = "cdc-pipeline"
EXEC = ["kubectl", "-n", NAMESPACE, "exec"]


def postgres(sql):
    return cdc_smoke.command(
        EXEC + [
            "deployment/cdc-postgres", "--", "sh", "-ec",
            'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -X -qAt '
            '-h 127.0.0.1 -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"',
            "cdc-smoke", sql,
        ]
    )


def trino_query(sql, timeout=30):
    # The local test identity sees unmasked synthetic records, but is read-only.
    return cdc_smoke.command(
        EXEC + [
            "deployment/cdc-trino", "--", "trino", "--user", "ci-smoke",
            "--catalog", "iceberg", "--schema", "analytics",
            "--output-format", "TSV", "--execute", sql,
        ],
        timeout=timeout,
    )


if __name__ == "__main__":
    cdc_smoke.postgres = postgres
    cdc_smoke.trino_query = trino_query
    cdc_smoke.main()
