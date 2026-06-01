"""Tests for GET /api/alerts and PATCH /api/alerts/{id}/ack."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import create_access_token
from main import app


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


class _AsyncCM:
    def __init__(self, conn: AsyncMock) -> None:
        self._conn = conn

    async def __aenter__(self) -> AsyncMock:
        return self._conn

    async def __aexit__(self, *_) -> bool:
        return False


def _make_pool(fake_conn: AsyncMock) -> MagicMock:
    pool = MagicMock()
    pool.acquire.return_value = _AsyncCM(fake_conn)
    return pool


def _auth_header() -> dict[str, str]:
    token, _ = create_access_token(username="admin", role="admin", user_id=1)
    return {"Authorization": f"Bearer {token}"}


def _alert_row(alert_id: int = 1, acked: bool = False) -> dict:
    return {
        "id": alert_id,
        "title": "Test alert",
        "severity": "HIGH",
        "details": None,
        "fired_at": datetime.now(timezone.utc),
        "acknowledged_at": datetime.now(timezone.utc) if acked else None,
        "acknowledged_by": "admin" if acked else None,
    }


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app.router.lifespan_context = _noop_lifespan

    fake_conn = AsyncMock()
    fake_conn.fetchrow.return_value = {
        "id": 1, "username": "admin", "role": "admin", "created_at": None
    }
    pool = _make_pool(fake_conn)

    monkeypatch.setattr("auth.get_pool", lambda: pool)
    monkeypatch.setattr("routers.alerts.get_pool", lambda: pool)

    with TestClient(app) as c:
        c._fake_conn = fake_conn
        yield c


def test_list_alerts_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/alerts")
    assert resp.status_code == 401


def test_list_alerts_empty(client: TestClient) -> None:
    client._fake_conn.fetch.return_value = []
    resp = client.get("/api/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_alerts_returns_items(client: TestClient) -> None:
    client._fake_conn.fetch.return_value = [_alert_row(1), _alert_row(2)]
    resp = client.get("/api/alerts", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["severity"] == "HIGH"


def test_acknowledge_alert(client: TestClient) -> None:
    client._fake_conn.fetchrow.side_effect = [
        {"id": 1, "username": "admin", "role": "admin", "created_at": None},
        _alert_row(1, acked=True),
    ]
    resp = client.patch(
        "/api/alerts/1/ack",
        json={"user": "admin"},
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert resp.json()["acknowledged_by"] == "admin"


def test_acknowledge_nonexistent_alert(client: TestClient) -> None:
    client._fake_conn.fetchrow.side_effect = [
        {"id": 1, "username": "admin", "role": "admin", "created_at": None},
        None,
    ]
    resp = client.patch(
        "/api/alerts/999/ack",
        json={"user": "admin"},
        headers=_auth_header(),
    )
    assert resp.status_code == 404
