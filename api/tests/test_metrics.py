"""Tests for GET /api/metrics/{layer}."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import app
from models import MetricsResponse, TableMetric


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


@pytest.fixture(autouse=True)
def reset_metrics_cache() -> None:
    """Flush the in-process metrics cache so tests don't share state."""
    import routers.metrics as m
    m._cache.clear()
    m._pending.clear()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c


def _fake_response(layer: str) -> MetricsResponse:
    return MetricsResponse(
        layer=layer,
        tables=[TableMetric(table=f"{layer}_customers_cdc", row_count=42)],
        cached=False,
        generated_at=datetime.now(timezone.utc),
    )


def test_metrics_unknown_layer_returns_400(client: TestClient) -> None:
    resp = client.get("/api/metrics/platinum")
    assert resp.status_code == 400
    assert "Unknown layer" in resp.json()["detail"]


@pytest.mark.parametrize("layer", ["bronze", "silver", "gold"])
def test_metrics_valid_layer(client: TestClient, layer: str) -> None:
    with patch(
        "routers.metrics._compute_metrics",
        new=AsyncMock(return_value=_fake_response(layer)),
    ):
        resp = client.get(f"/api/metrics/{layer}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["layer"] == layer
    assert isinstance(body["tables"], list)
    assert body["tables"][0]["row_count"] == 42


def test_metrics_cache_flag(client: TestClient) -> None:
    result = _fake_response("bronze")
    with patch(
        "routers.metrics._compute_metrics",
        new=AsyncMock(return_value=result),
    ):
        r1 = client.get("/api/metrics/bronze")
        r2 = client.get("/api/metrics/bronze")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
