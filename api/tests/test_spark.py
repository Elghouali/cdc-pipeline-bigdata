"""Tests for GET /api/spark/jobs and GET /api/spark/running."""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import app
from routers.spark import _summarize_application


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


@pytest.fixture()
def client() -> TestClient:
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c


# ── _summarize_application unit tests ────────────────────────────────────────

def test_summarize_running_application() -> None:
    app_data = {
        "id": "app-001",
        "name": "cdc-bronze-ingestion",
        "attempts": [{"completed": False, "startTime": "2026-06-01T00:00:00",
                       "endTime": None, "duration": 0, "sparkUser": "root"}],
    }
    result = _summarize_application(app_data)
    assert result["status"] == "running"
    assert result["name"] == "cdc-bronze-ingestion"


def test_summarize_completed_application() -> None:
    app_data = {
        "id": "app-002",
        "name": "cdc-gold-aggregation",
        "attempts": [{"completed": True, "startTime": "t", "endTime": "t",
                       "duration": 3600000, "sparkUser": "root"}],
    }
    result = _summarize_application(app_data)
    assert result["status"] == "completed"


def test_summarize_no_attempts() -> None:
    result = _summarize_application({"id": "app-003", "name": "test", "attempts": []})
    assert result["id"] == "app-003"


# ── HTTP endpoint tests ───────────────────────────────────────────────────────

def _mock_response(status_code: int, json_body) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    return resp


def test_spark_jobs_empty(client: TestClient) -> None:
    with patch("routers.spark.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(return_value=_mock_response(200, []))
        resp = client.get("/api/spark/jobs")

    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_spark_jobs_returns_summarized(client: TestClient) -> None:
    apps = [
        {"id": "app-001", "name": "cdc-bronze",
         "attempts": [{"completed": True, "startTime": "t", "endTime": "t",
                        "duration": 1000, "sparkUser": "root"}]},
    ]
    with patch("routers.spark.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(return_value=_mock_response(200, apps))
        resp = client.get("/api/spark/jobs")

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["jobs"][0]["name"] == "cdc-bronze"


def test_spark_jobs_unreachable(client: TestClient) -> None:
    with patch("routers.spark.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        resp = client.get("/api/spark/jobs")

    assert resp.status_code == 503


def test_spark_running_empty(client: TestClient) -> None:
    payload = {"status": "ALIVE", "activeapps": []}
    with patch("routers.spark.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(return_value=_mock_response(200, payload))
        resp = client.get("/api/spark/running")

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["master_status"] == "ALIVE"
