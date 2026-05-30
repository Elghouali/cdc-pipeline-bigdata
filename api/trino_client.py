"""Async Trino HTTP client used by the metrics and query routers.

Trino's REST protocol is multi-stage: an initial POST /v1/statement returns
a `nextUri` that must be polled until `nextUri` is absent. Callers:
api/routers/metrics.py, api/routers/query.py.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import httpx

from config import settings

logger = logging.getLogger("cdc-api.trino")

_STATEMENT_PATH = "/v1/statement"
_POLL_DELAY_SECONDS = 0.15


class TrinoError(RuntimeError):
    """Raised when Trino returns a query-level error."""


def _headers() -> dict[str, str]:
    return {
        "X-Trino-User": settings.trino_user,
        "X-Trino-Source": "cdc-api",
        "Content-Type": "text/plain",
    }


async def stream_query(sql: str) -> AsyncIterator[dict[str, Any]]:
    """Execute `sql` against Trino and yield row dicts as they arrive.

    Each yielded item maps column name -> value for one result row.
    """
    async with httpx.AsyncClient(base_url=settings.trino_url, timeout=10.0) as client:
        try:
            response = await client.post(
                _STATEMENT_PATH, content=sql.encode("utf-8"), headers=_headers()
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TrinoError(f"HTTP connection error: {exc}")

        try:
            body: dict[str, Any] = response.json()
        except json.JSONDecodeError as exc:
            raise TrinoError(f"Invalid JSON in Trino response: {exc}")

        columns: list[str] | None = None

        while True:
            error = body.get("error")
            if error is not None:
                message = error.get("message", "Unknown Trino error")
                raise TrinoError(message)

            if body.get("columns"):
                columns = [col["name"] for col in body["columns"]]

            for row in body.get("data", []) or []:
                if columns is None:
                    continue
                yield dict(zip(columns, row))

            next_uri: str | None = body.get("nextUri")
            if not next_uri:
                break

            await asyncio.sleep(_POLL_DELAY_SECONDS)
            try:
                poll = await client.get(next_uri, headers=_headers())
                poll.raise_for_status()
            except httpx.HTTPError as exc:
                raise TrinoError(f"HTTP polling error: {exc}")
            
            try:
                body = poll.json()
            except json.JSONDecodeError as exc:
                raise TrinoError(f"Invalid JSON in Trino poll response: {exc}")


async def fetch_all(sql: str) -> list[dict[str, Any]]:
    """Execute `sql` and return all result rows materialized as a list."""
    return [row async for row in stream_query(sql)]
