"""Pipeline alerts router. Lists alerts and acknowledges them.

Caller: api/main.py. Endpoints: GET /api/alerts,
PATCH /api/alerts/{id}/ack (authentication required).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user
from db import get_pool
from models import Alert, AlertAck, User

logger = logging.getLogger("cdc-api.alerts")

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_MAX_ALERTS = 200


@router.get("", response_model=list[Alert])
async def list_alerts(
    acknowledged: bool | None = None,
    _user: User = Depends(get_current_user),
) -> list[Alert]:
    """Return pipeline alerts, optionally filtered by acknowledgement state."""
    pool = get_pool()
    query = (
        "SELECT id, title, severity, details, fired_at, acknowledged_at, acknowledged_by "
        "FROM pipeline_alerts"
    )
    if acknowledged is True:
        query += " WHERE acknowledged_at IS NOT NULL"
    elif acknowledged is False:
        query += " WHERE acknowledged_at IS NULL"
    query += f" ORDER BY fired_at DESC LIMIT {_MAX_ALERTS}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query)

    return [
        Alert(
            id=r["id"],
            title=r["title"],
            severity=r["severity"],
            details=dict(r["details"]) if r["details"] is not None else None,
            fired_at=r["fired_at"],
            acknowledged_at=r["acknowledged_at"],
            acknowledged_by=r["acknowledged_by"],
        )
        for r in rows
    ]


@router.patch("/{alert_id}/ack", response_model=Alert)
async def acknowledge_alert(
    alert_id: int,
    body: AlertAck,
    _user: User = Depends(get_current_user),
) -> Alert:
    """Mark an alert acknowledged, recording who acknowledged it and when."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE pipeline_alerts "
            "SET acknowledged_at = NOW(), acknowledged_by = $1 "
            "WHERE id = $2 "
            "RETURNING id, title, severity, details, fired_at, "
            "acknowledged_at, acknowledged_by",
            body.user,
            alert_id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} was not found.",
        )

    logger.info("Alert %d acknowledged by '%s'.", alert_id, body.user)
    return Alert(
        id=row["id"],
        title=row["title"],
        severity=row["severity"],
        details=dict(row["details"]) if row["details"] is not None else None,
        fired_at=row["fired_at"],
        acknowledged_at=row["acknowledged_at"],
        acknowledged_by=row["acknowledged_by"],
    )
