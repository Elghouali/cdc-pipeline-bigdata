"""Ad-hoc SQL query router. Streams Trino results as newline-delimited JSON.

Caller: api/main.py. Endpoint: POST /api/query (authentication required).
"""

import json
import logging
import re
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from auth import get_current_user
from models import QueryRequest, User
from trino_client import TrinoError, stream_query

logger = logging.getLogger("cdc-api.query")

router = APIRouter(prefix="/api", tags=["query"])

# Statement keywords that mutate data or schema — rejected outright.
_BLOCKED_KEYWORDS = (
    "DROP",
    "CREATE",
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "CALL",
)
_BLOCKED_PATTERN = re.compile(
    r"\b(" + "|".join(_BLOCKED_KEYWORDS) + r")\b", re.IGNORECASE
)
_COMMENT_PATTERN = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


def _strip_comments(sql: str) -> str:
    return _COMMENT_PATTERN.sub(" ", sql)


def _validate_sql(sql: str) -> str:
    """Return cleaned SQL or raise HTTPException(400) for unsafe statements."""
    cleaned = _strip_comments(sql).strip().rstrip(";").strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SQL statement is empty.",
        )
    if ";" in cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple statements are not allowed.",
        )
    blocked = _BLOCKED_PATTERN.search(cleaned)
    if blocked is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Statement keyword '{blocked.group(1).upper()}' is not permitted. "
            "Only read-only queries are allowed.",
        )
    return cleaned


async def _ndjson_stream(sql: str) -> AsyncIterator[bytes]:
    try:
        async for row in stream_query(sql):
            yield (json.dumps(row, default=str) + "\n").encode("utf-8")
    except TrinoError as exc:
        yield (json.dumps({"error": str(exc)}) + "\n").encode("utf-8")
    except Exception as exc:  # noqa: BLE001 - surface as a stream-level error line
        logger.exception("Unexpected error while streaming query results.")
        yield (json.dumps({"error": str(exc)}) + "\n").encode("utf-8")


@router.post("/query")
async def run_query(
    body: QueryRequest, user: User = Depends(get_current_user)
) -> StreamingResponse:
    """Execute a read-only SQL query and stream rows as NDJSON."""
    cleaned = _validate_sql(body.sql)
    logger.info("User '%s' running query.", user.username)
    return StreamingResponse(
        _ndjson_stream(cleaned),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store"},
    )
