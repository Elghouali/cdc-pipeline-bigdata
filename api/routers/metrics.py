"""Layer-metrics router. Reports row counts and latest partition per table.

Caller: api/main.py. Endpoint: GET /api/metrics/{layer}.
Results are cached in-process for 30 seconds per layer.

NOTE: When running with multiple uvicorn workers (prod Dockerfile), each worker
process maintains its own cache. The cache reduces Trino load per worker but does
not coordinate across workers. For a shared cache, replace _cache with Redis.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from config import ICEBERG_CATALOG, ICEBERG_SCHEMA, LAYER_PREFIXES
from models import MetricsResponse, TableMetric
from trino_client import TrinoError, fetch_all

logger = logging.getLogger("cdc-api.metrics")

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_CACHE_TTL_SECONDS = 30.0
# layer -> (response, monotonic_timestamp)
_cache: dict[str, tuple[MetricsResponse, float]] = {}
# layer -> asyncio.Future that resolves once the in-flight computation finishes.
# Any request that arrives while a computation is running waits on this future
# rather than launching a duplicate Trino query.
_pending: dict[str, asyncio.Future[MetricsResponse]] = {}
_cache_lock = asyncio.Lock()


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


async def _metric_for_table(table: str) -> TableMetric:
    try:
        # Use Iceberg $snapshots metadata — reads metadata.json, not Parquet files.
        # Explicit aliases let us access columns by name, not fragile position.
        query = (
            f"SELECT summary['total-records'] AS row_count, "
            f"CAST(committed_at AS VARCHAR) AS partition_ts "
            f"FROM {ICEBERG_CATALOG}.{ICEBERG_SCHEMA}.\"{table}$snapshots\" "
            "ORDER BY committed_at DESC LIMIT 1"
        )
        rows = await fetch_all(query)

        if rows:
            row_count_str = rows[0].get("row_count")
            latest_partition = rows[0].get("partition_ts")
            row_count = int(row_count_str) if row_count_str else 0
        else:
            row_count = 0
            latest_partition = None

        return TableMetric(
            table=table,
            row_count=row_count,
            latest_partition=latest_partition,
        )
    except (TrinoError, ValueError) as exc:
        logger.warning("Metric collection failed for %s: %s", table, exc)
        return TableMetric(table=table, error=str(exc))


async def _metric_for_table_safe(table: str) -> TableMetric:
    try:
        return await asyncio.wait_for(_metric_for_table(table), timeout=25.0)
    except asyncio.TimeoutError:
        logger.warning("Timeout collecting metrics for %s", table)
        return TableMetric(table=table, error="Timeout (query too slow)")
    except Exception as exc:
        logger.warning("Metric collection failed for %s: %s", table, exc)
        return TableMetric(table=table, error=str(exc))


async def _compute_metrics(layer: str) -> MetricsResponse:
    """Run the Trino queries to build a fresh MetricsResponse for `layer`."""
    try:
        tables = await asyncio.wait_for(
            _list_tables(LAYER_PREFIXES[layer]),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Trino query timed out after 5 seconds",
        )
    except TrinoError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Trino query failed: {exc}",
        )

    metrics_results = await asyncio.gather(*(_metric_for_table_safe(t) for t in tables))

    return MetricsResponse(
        layer=layer,  # type: ignore[arg-type]
        tables=list(metrics_results),
        cached=False,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/{layer}", response_model=MetricsResponse)
async def layer_metrics(layer: str) -> MetricsResponse:
    """Return per-table row counts and latest partitions for one layer."""
    if layer not in LAYER_PREFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown layer '{layer}'. Expected bronze, silver, or gold.",
        )

    async with _cache_lock:
        # Serve from cache if fresh.
        cached = _cache.get(layer)
        if cached is not None and (time.monotonic() - cached[1]) < _CACHE_TTL_SECONDS:
            return cached[0].model_copy(update={"cached": True})

        # If another coroutine is already computing this layer, wait for it.
        if layer in _pending:
            future = _pending[layer]
        else:
            # We are the first; register a future so subsequent requests wait.
            future: asyncio.Future[MetricsResponse] = asyncio.get_running_loop().create_future()
            _pending[layer] = future
            future = None  # signal that we must compute

    if future is not None:
        # Wait for the in-flight computation started by another coroutine.
        return await future

    # We hold no lock here; compute the expensive queries without blocking others.
    try:
        response = await _compute_metrics(layer)
    except Exception as exc:
        # Resolve pending waiters with the original exception so they don't hang
        # and receive the correct HTTP status code (e.g. 504, 502).
        async with _cache_lock:
            fut = _pending.pop(layer, None)
        if fut and not fut.done():
            fut.set_exception(exc)
        raise

    async with _cache_lock:
        _cache[layer] = (response, time.monotonic())
        fut = _pending.pop(layer, None)

    if fut and not fut.done():
        fut.set_result(response)

    return response
