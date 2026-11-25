"""Basic tests for the CDC API service.

Verifies the app imports cleanly and the health endpoint responds 200
without requiring live Postgres/Trino/Kafka backends (externals are stubbed).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import routers.health as health_module
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from main import app
from models import HealthItem
from routers.query import _validate_sql


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Replacement lifespan that skips DB/Kafka initialization for tests."""
    yield


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Provide a TestClient with external service checks stubbed out."""

    async def _fake_check_http(service: str, url: str, ok: set[int]) -> HealthItem:
        return HealthItem(service=service, status="up", latency_ms=1)

    async def _fake_check_postgres() -> HealthItem:
        return HealthItem(service="postgres", status="up", latency_ms=1)

    monkeypatch.setattr(health_module, "_check_http", _fake_check_http)
    monkeypatch.setattr(health_module, "_check_postgres", _fake_check_postgres)

    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as test_client:
        yield test_client


def test_app_imports() -> None:
    """The FastAPI app object exists and exposes routes."""
    assert app.title == "CDC Pipeline API"
    assert len(app.routes) > 0


def test_root_endpoint(client: TestClient) -> None:
    """The service banner endpoint responds with 200 and metadata."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "cdc-pipeline-api"


def test_health_returns_200(client: TestClient) -> None:
    """GET /api/health returns 200 and a list of service health items."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    services = {item["service"] for item in body}
    assert {"trino", "kafka-connect", "postgres"}.issubset(services)
    for item in body:
        assert item["status"] in ("up", "down")


def test_query_blocks_ddl() -> None:
    """The SQL validator rejects data-mutating statements."""
    with pytest.raises(HTTPException) as exc_info:
        _validate_sql("DROP TABLE iceberg.analytics.gold_orders")
    assert exc_info.value.status_code == 400


def test_query_allows_select() -> None:
    """The SQL validator accepts a plain read-only SELECT."""
    cleaned = _validate_sql("SELECT 1")
    assert "SELECT" in cleaned.upper()
