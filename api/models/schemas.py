"""Pydantic v2 schemas for the CDC API service.

Defines request/response models used across routers. No data-file I/O.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["admin", "viewer"]


class User(BaseModel):
    """A pipeline-console user record (without the password hash)."""

    id: int
    username: str
    role: Role
    created_at: datetime | None = None


class LoginRequest(BaseModel):
    """Credentials submitted to POST /auth/login."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class Token(BaseModel):
    """JWT access token returned by POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds.")
    role: Role
    username: str


class QueryRequest(BaseModel):
    """Body of POST /api/query."""

    sql: str = Field(min_length=1, max_length=20_000)


class AlertAck(BaseModel):
    """Body of PATCH /api/alerts/{id}/ack."""

    user: str = Field(min_length=1, max_length=100)


class HealthItem(BaseModel):
    """Health status for a single internal service."""

    service: str
    status: Literal["up", "down"]
    latency_ms: int | None = None
    detail: str | None = None


class TableMetric(BaseModel):
    """Row-count and partition info for a single Iceberg table."""

    table: str
    row_count: int | None = None
    latest_partition: str | None = None
    error: str | None = None


class MetricsResponse(BaseModel):
    """Aggregated metrics for one medallion layer."""

    layer: Literal["bronze", "silver", "gold"]
    tables: list[TableMetric]
    cached: bool = False
    generated_at: datetime


class Alert(BaseModel):
    """A pipeline alert row from the pipeline_alerts table."""

    id: int
    title: str
    severity: str
    details: dict[str, Any] | None = None
    fired_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
