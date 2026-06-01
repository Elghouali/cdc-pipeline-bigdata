"""Tests for POST /auth/login, POST /auth/logout, GET /auth/me."""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import create_access_token
from db import hash_password
from main import app


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


class _AsyncCM:
    """Async context manager that yields a pre-built fake connection."""
    def __init__(self, conn: AsyncMock) -> None:
        self._conn = conn

    async def __aenter__(self) -> AsyncMock:
        return self._conn

    async def __aexit__(self, *_) -> bool:
        return False


class _FakeRecord(dict):
    """Minimal asyncpg Record stand-in that supports item access."""
    pass


def _make_user_record(
    username: str = "admin",
    role: str = "admin",
    password: str = "adminpass",
) -> _FakeRecord:
    return _FakeRecord(
        id=1,
        username=username,
        password_hash=hash_password(password),
        role=role,
        created_at=None,
    )


def _make_pool(fake_conn: AsyncMock) -> MagicMock:
    pool = MagicMock()
    pool.acquire.return_value = _AsyncCM(fake_conn)
    return pool


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app.router.lifespan_context = _noop_lifespan

    fake_conn = AsyncMock()
    fake_conn.fetchrow.return_value = _make_user_record()
    pool = _make_pool(fake_conn)

    monkeypatch.setattr("routers.auth.get_pool", lambda: pool)
    monkeypatch.setattr("auth.get_pool", lambda: pool)

    with TestClient(app) as c:
        c._fake_conn = fake_conn
        yield c


def test_login_success(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert body["username"] == "admin"
    assert body["role"] == "admin"


def test_login_wrong_password(client: TestClient) -> None:
    client._fake_conn.fetchrow.return_value = _make_user_record(password="realpass")
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient) -> None:
    client._fake_conn.fetchrow.return_value = None
    resp = client.post("/auth/login", json={"username": "ghost", "password": "any"})
    assert resp.status_code == 401


def test_login_empty_username_rejected(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"username": "", "password": "pass"})
    assert resp.status_code == 422


def test_logout_always_200(client: TestClient) -> None:
    resp = client.post("/auth/logout")
    assert resp.status_code == 200


def test_me_returns_user(client: TestClient) -> None:
    token, _ = create_access_token(username="admin", role="admin", user_id=1)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_me_unauthenticated(client: TestClient) -> None:
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client: TestClient) -> None:
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code == 401
