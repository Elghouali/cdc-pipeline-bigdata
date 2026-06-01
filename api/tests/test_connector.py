"""Tests for GET /api/connector/status and POST /api/connector/restart."""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import create_access_token
from main import app


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


def _admin_header() -> dict[str, str]:
    token, _ = create_access_token(username="admin", role="admin", user_id=1)
    return {"Authorization": f"Bearer {token}"}


def _viewer_header() -> dict[str, str]:
    token, _ = create_access_token(username="viewer", role="viewer", user_id=2)
    return {"Authorization": f"Bearer {token}"}


class _AsyncCM:
    def __init__(self, conn: AsyncMock) -> None:
        self._conn = conn

    async def __aenter__(self) -> AsyncMock:
        return self._conn

    async def __aexit__(self, *_) -> bool:
        return False


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app.router.lifespan_context = _noop_lifespan

    fake_conn = AsyncMock()

    def _user_for(username: str) -> dict:
        role = "admin" if username == "admin" else "viewer"
        return {"id": 1, "username": username, "role": role, "created_at": None}

    fake_conn.fetchrow.side_effect = lambda q, username: _user_for(username)

    pool = MagicMock()
    pool.acquire.return_value = _AsyncCM(fake_conn)
    monkeypatch.setattr("auth.get_pool", lambda: pool)

    with TestClient(app) as c:
        yield c


def _mock_response(status_code: int, json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


def test_connector_status_ok(client: TestClient) -> None:
    payload = {"name": "cdc-postgres", "connector": {"state": "RUNNING"}}

    with patch("routers.connector.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(return_value=_mock_response(200, payload))
        resp = client.get("/api/connector/status")

    assert resp.status_code == 200
    assert resp.json()["name"] == "cdc-postgres"


def test_connector_status_not_registered(client: TestClient) -> None:
    with patch("routers.connector.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(return_value=_mock_response(404, {}))
        resp = client.get("/api/connector/status")

    assert resp.status_code == 404


def test_connector_status_unreachable(client: TestClient) -> None:
    with patch("routers.connector.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        resp = client.get("/api/connector/status")

    assert resp.status_code == 503


def test_connector_restart_requires_admin(client: TestClient) -> None:
    resp = client.post("/api/connector/restart", headers=_viewer_header())
    assert resp.status_code == 403


def test_connector_restart_accepted(client: TestClient) -> None:
    with patch("routers.connector.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_cls)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_cls.post = AsyncMock(return_value=_mock_response(202, {}))
        resp = client.post("/api/connector/restart", headers=_admin_header())

    assert resp.status_code == 202
