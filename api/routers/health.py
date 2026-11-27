"""Health-check router. Probes each internal pipeline service in parallel.

Caller: api/main.py (app.include_router). Endpoint: GET /api/health.
"""

import asyncio
import logging
import os
import time

import asyncpg
import httpx
from fastapi import APIRouter
from models import HealthItem
from spark_runtime import driver_urls

from config import settings

logger = logging.getLogger("cdc-api.health")

router = APIRouter(prefix="/api", tags=["health"])

_CHECK_TIMEOUT_SECONDS = 3.0
# MinIO is reachable on the docker network; derived from the standard endpoint.
_MINIO_HEALTH_URL = os.getenv("MINIO_HEALTH_URL", "http://minio:9000/minio/health/live")


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


async def _check_http(service: str, url: str, ok_statuses: set[int]) -> HealthItem:
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=_CHECK_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
        if resp.status_code in ok_statuses:
            return HealthItem(
                service=service, status="up", latency_ms=_elapsed_ms(start)
            )
        return HealthItem(
            service=service,
            status="down",
            latency_ms=_elapsed_ms(start),
            detail=f"HTTP {resp.status_code}",
        )
    except httpx.HTTPError as exc:
        # httpx raises httpx.TimeoutException (subclass of HTTPError) on timeout,
        # not asyncio.TimeoutError — so HTTPError covers all cases here.
        return HealthItem(
            service=service,
            status="down",
            latency_ms=_elapsed_ms(start),
            detail=str(exc) or exc.__class__.__name__,
        )


async def _check_postgres() -> HealthItem:
    start = time.perf_counter()
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(dsn=settings.database_url),
            timeout=_CHECK_TIMEOUT_SECONDS,
        )
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()
        return HealthItem(
            service="postgres", status="up", latency_ms=_elapsed_ms(start)
        )
    except (TimeoutError, asyncpg.PostgresError, OSError) as exc:
        return HealthItem(
            service="postgres",
            status="down",
            latency_ms=_elapsed_ms(start),
            detail=str(exc) or exc.__class__.__name__,
        )


@router.get("/health", response_model=list[HealthItem])
async def health() -> list[HealthItem]:
    """Return up/down status and latency for every internal service."""
    drivers = driver_urls()
    spark_checks = (
        [
            _check_http(f"spark-{layer}", f"{url}/api/v1/applications", {200})
            for layer, url in drivers.items()
        ]
        if drivers
        else [
            _check_http("spark-master", f"{settings.spark_master_url}/json", {200, 302})
        ]
    )
    results = await asyncio.gather(
        _check_http("trino", f"{settings.trino_url}/v1/status", {200}),
        _check_http("kafka-connect", f"{settings.kafka_connect_url}/connectors", {200}),
        *spark_checks,
        _check_http("minio", _MINIO_HEALTH_URL, {200}),
        _check_postgres(),
    )
    return list(results)
