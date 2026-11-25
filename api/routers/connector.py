"""Kafka Connect proxy router for the Debezium CDC connector.

Caller: api/main.py. Endpoints: GET /api/connector/status,
POST /api/connector/restart (admin only).
"""

import logging
from typing import Any

import httpx
from auth import require_admin
from fastapi import APIRouter, Depends, HTTPException, status
from models import User

from config import settings

logger = logging.getLogger("cdc-api.connector")

router = APIRouter(prefix="/api/connector", tags=["connector"])

_TIMEOUT_SECONDS = 5.0


def _connector_base() -> str:
    return f"{settings.kafka_connect_url}/connectors/{settings.connector_name}"


@router.get("/status")
async def connector_status() -> dict[str, Any]:
    """Return the Debezium connector and task status from Kafka Connect."""
    url = f"{_connector_base()}/status"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Kafka Connect is unreachable: {exc}",
        ) from exc

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{settings.connector_name}' is not registered.",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Kafka Connect returned HTTP {resp.status_code}.",
        )
    return resp.json()


@router.post("/restart", status_code=status.HTTP_202_ACCEPTED)
async def connector_restart(
    _admin: User = Depends(require_admin),
) -> dict[str, str]:
    """Restart the Debezium connector. Requires the admin role."""
    # includeTasks=true restarts failed tasks alongside the connector itself.
    url = f"{_connector_base()}/restart?includeTasks=true&onlyFailed=false"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(url)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Kafka Connect is unreachable: {exc}",
        ) from exc

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{settings.connector_name}' is not registered.",
        )
    if resp.status_code not in (200, 202, 204):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Kafka Connect returned HTTP {resp.status_code}.",
        )
    logger.info("Connector '%s' restart requested.", settings.connector_name)
    return {"detail": f"Restart requested for connector '{settings.connector_name}'."}
