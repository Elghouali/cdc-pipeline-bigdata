"""Tests for POST /api/query (SQL validation and streaming)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from auth import create_access_token
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from main import app
from routers.query import _validate_sql


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


# ── _validate_sql unit tests (no HTTP involved) ───────────────────────────────


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT * FROM iceberg.analytics.gold_orders",
        "  select id from bronze_customers_cdc  ",
        "SELECT * FROM t WHERE status = 'CREATE_PENDING'",  # keyword inside string
        "SELECT * FROM t WHERE note = 'UPDATE me'",  # keyword inside string
    ],
)
def test_validate_sql_allows_reads(sql: str) -> None:
    result = _validate_sql(sql)
    assert result


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE iceberg.analytics.gold_orders",
        "CREATE TABLE foo (id INT)",
        "INSERT INTO foo VALUES (1)",
        "UPDATE foo SET x = 1",
        "DELETE FROM foo",
        "ALTER TABLE foo ADD COLUMN y INT",
        "TRUNCATE TABLE foo",
        "MERGE INTO t USING s ON t.id=s.id WHEN MATCHED THEN UPDATE SET t.x=s.x",
        "/* comment */ DROP TABLE t",
        "-- comment\nDROP TABLE t",
        "CALL some_procedure()",
        "SET SESSION query_max_run_time = '1h'",
        "EXECUTE prepared_query",
    ],
)
def test_validate_sql_blocks_mutations(sql: str) -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_sql(sql)
    assert exc.value.status_code == 400


def test_validate_sql_rejects_empty() -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_sql("   ")
    assert exc.value.status_code == 400


def test_validate_sql_rejects_multiple_statements() -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_sql("SELECT 1; SELECT 2")
    assert exc.value.status_code == 400


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


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
    fake_conn.fetchrow.return_value = {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "created_at": None,
    }
    pool = MagicMock()
    pool.acquire.return_value = _AsyncCM(fake_conn)
    monkeypatch.setattr("auth.get_pool", lambda: pool)

    with TestClient(app) as c:
        yield c


def _auth_header() -> dict[str, str]:
    token, _ = create_access_token(username="admin", role="admin", user_id=1)
    return {"Authorization": f"Bearer {token}"}


def test_query_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/query", json={"sql": "SELECT 1"})
    assert resp.status_code == 401


def test_query_streams_results(client: TestClient) -> None:
    async def _fake_stream(sql: str):
        yield {"id": 1, "name": "Alice"}
        yield {"id": 2, "name": "Bob"}

    with patch("routers.query.stream_query", side_effect=_fake_stream):
        resp = client.post(
            "/api/query",
            json={"sql": "SELECT id, name FROM silver_customers"},
            headers=_auth_header(),
        )
    assert resp.status_code == 200
    lines = [ln for ln in resp.text.strip().splitlines() if ln]
    assert len(lines) == 2


def test_query_rejects_ddl_via_http(client: TestClient) -> None:
    resp = client.post(
        "/api/query",
        json={"sql": "DROP TABLE gold_orders"},
        headers=_auth_header(),
    )
    assert resp.status_code == 400
