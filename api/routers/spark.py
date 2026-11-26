"""Spark proxy router. Surfaces job history and currently running apps.

Caller: api/main.py. Endpoints: GET /api/spark/jobs, GET /api/spark/running.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status

from config import settings
from spark_runtime import driver_urls, live_applications

logger = logging.getLogger("cdc-api.spark")

router = APIRouter(prefix="/api/spark", tags=["spark"])

_TIMEOUT_SECONDS = 5.0
_MAX_JOBS = 20


async def _get_json(url: str, service: str) -> Any:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service} returned HTTP {exc.response.status_code}.",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service} is unreachable: {exc}",
        ) from exc


def _summarize_application(app: dict[str, Any]) -> dict[str, Any]:
    attempts = app.get("attempts") or [{}]
    latest = attempts[0]
    return {
        "id": app.get("id"),
        "name": app.get("name"),
        "status": "running" if not latest.get("completed", True) else "completed",
        "started_at": latest.get("startTime"),
        "ended_at": latest.get("endTime"),
        "duration_ms": latest.get("duration"),
        "spark_user": latest.get("sparkUser"),
    }


@router.get("/jobs")
async def spark_jobs() -> dict[str, Any]:
    """Return the last 20 Spark applications from the History Server."""
    if driver_urls():
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            apps = await live_applications(client)
        jobs = [_summarize_application(app) for items in apps.values() for app in items]
        return {"count": len(jobs), "jobs": jobs, "history_available": False}
    url = f"{settings.spark_history_url}/api/v1/applications?limit={_MAX_JOBS}"
    applications = await _get_json(url, "Spark History Server")
    if not isinstance(applications, list):
        applications = []
    jobs = [_summarize_application(app) for app in applications[:_MAX_JOBS]]
    return {"count": len(jobs), "jobs": jobs}


@router.get("/running")
async def spark_running() -> dict[str, Any]:
    """Return apps currently running on the Spark master."""
    if driver_urls():
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            apps = await live_applications(client)
        running = [
            {
                "id": app.get("id"),
                "name": app.get("name"),
                "cores": None,
                "memory_per_executor": None,
                "submitted_at": (app.get("attempts") or [{}])[0].get("startTime"),
                "state": "RUNNING",
                "duration_ms": (app.get("attempts") or [{}])[0].get("duration"),
            }
            for items in apps.values()
            for app in items
        ]
        return {"count": len(running), "running": running, "master_status": None}
    payload = await _get_json(f"{settings.spark_master_url}/json", "Spark Master")
    active = payload.get("activeapps", []) if isinstance(payload, dict) else []
    running = [
        {
            "id": app.get("id"),
            "name": app.get("name"),
            "cores": app.get("cores"),
            "memory_per_executor": app.get("memoryperexecutor"),
            "submitted_at": app.get("submitdate"),
            "state": app.get("state"),
            "duration_ms": app.get("duration"),
        }
        for app in active
    ]
    return {
        "count": len(running),
        "running": running,
        "master_status": payload.get("status") if isinstance(payload, dict) else None,
    }
