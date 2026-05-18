"""Layer-metrics router. Reports row counts and latest partition per table.

Caller: api/main.py. Endpoint: GET /api/metrics/{layer}.
Results are cached in-process for 30 seconds per layer.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from config import ICEBERG_CATALOG, ICEBERG_SCHEMA, LAYER_PREFIXES
from models import MetricsResponse, TableMetric
from trino_client import TrinoError, fetch_all, fetch_scalar

logger = logging.getLogger("cdc-api.metrics")

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_CACHE_TTL_SECONDS = 30.0
# layer -> (response, monotonic_timestamp)
_cache: dict[str, tuple[MetricsResponse, float]] = {}
_cache_lock = asyncio.Lock()

# Candidate partition columns, ordered by preference, across medallion layers.
_PARTITION_COLUMNS = ("snapshot_date", "_ingest_date", "ingest_date", "event_date")


def _qualified(table: str) -> str:
    return f"{ICEBERG_CATALOG}.{ICEBERG_SCHEMA}.{table}"


async def _list_tables(prefix: str) -> list[str]:
    rows = await fetch_all(
        "SELECT table_name FROM "
        f"{ICEBERG_CATALOG}.information_schema.tables "
        f"WHERE table_schema = '{ICEBERG_SCHEMA}' "
        f"AND table_name LIKE '{prefix}%' "
        "ORDER BY table_name"
    )
    return [str(r["table_name"]) for r in rows]


async def _table_columns(table: str) -> set[str]:
    rows = await fetch_all(
        "SELECT column_name FROM "
        f"{ICEBERG_CATALOG}.information_schema.columns "
        f"WHERE table_schema = '{ICEBERG_SCHEMA}' "
        f"AND table_name = '{table}'"
    )
    return {str(r["column_name"]) for r in rows}


async def _metric_for_table(table: str) -> TableMetric:
    try:
        row_count = await fetch_scalar(f"SELECT COUNT(*) FROM {_qualified(table)}")
        columns = await _table_columns(table)
        latest_partition: str | None = None
        for candidate in _PARTITION_COLUMNS:
            if candidate in columns:
                value = await fetch_scalar(
                    f"SELECT MAX({candidate}) FROM {_qualified(table)}"
                )
                latest_partition = None if value is None else str(value)
                break
        return TableMetric(
            table=table,
            row_count=int(row_count) if row_count is not None else 0,
            latest_partition=latest_partition,
        )
    except (TrinoError, ValueError) as exc:
        logger.warning("Metric collection failed for %s: %s", table, exc)
        return TableMetric(table=table, error=str(exc))


@router.get("/{layer}", response_model=MetricsResponse)
async def layer_metrics(layer: str) -> MetricsResponse:
    """Return per-table row counts and latest partitions for one layer."""
    if layer not in LAYER_PREFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown layer '{layer}'. Expected bronze, silver, or gold.",
        )

    async with _cache_lock:
        cached = _cache.get(layer)
        if cached is not None and (time.monotonic() - cached[1]) < _CACHE_TTL_SECONDS:
            return cached[0].model_copy(update={"cached": True})

    try:
        tables = await _list_tables(LAYER_PREFIXES[layer])
    except TrinoError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Trino query failed: {exc}",
        )

    metrics = await asyncio.gather(*(_metric_for_table(t) for t in tables))
    response = MetricsResponse(
        layer=layer,  # type: ignore[arg-type]
        tables=list(metrics),
        cached=False,
        generated_at=datetime.now(timezone.utc),
    )

    async with _cache_lock:
        _cache[layer] = (response, time.monotonic())
    return response
