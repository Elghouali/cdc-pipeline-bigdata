"""Ad-hoc SQL query router. Streams Trino results as newline-delimited JSON.

Caller: api/main.py. Endpoint: POST /api/query (authentication required).
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from contextlib import aclosing

from auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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
# Matches single-quoted string literals (handles escaped quotes via '' doubling).
_STRING_LITERAL_PATTERN = re.compile(r"'(?:[^'\\]|\\.)*'")


def _strip_comments(sql: str) -> str:
    return _COMMENT_PATTERN.sub(" ", sql)


def _strip_string_literals(sql: str) -> str:
    """Replace string literals with '' so blocked-keyword check avoids false positives.

    Without this, a query like WHERE status = 'CREATE_PENDING' would be rejected
    even though CREATE appears only inside a string value.
    """
    return _STRING_LITERAL_PATTERN.sub("''", sql)


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
    if not re.match(r"^(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN)\b", cleaned, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Only read queries are permitted.")
    blocked = _BLOCKED_PATTERN.search(_strip_string_literals(cleaned))
    if blocked is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Statement keyword '{blocked.group(1).upper()}' is not permitted. "
            "Only read-only queries are allowed.",
        )
    return cleaned


async def _ndjson_stream(sql: str) -> AsyncIterator[bytes]:
    try:
        async with asyncio.timeout(60), aclosing(stream_query(sql)) as rows:
            count = 0
            async for row in rows:
                if count >= 10000:
                    yield b'{"error":"Result limit exceeded (10000 rows)."}\n'
                    return
                count += 1
                yield (json.dumps(row, default=str) + "\n").encode("utf-8")
    except TimeoutError:
        yield b'{"error":"Query exceeded the 60 second deadline."}\n'
    except TrinoError as exc:
        logger.warning("Trino query failed: %s", exc)
        yield b'{"error":"Query failed or access denied."}\n'
    except Exception:
        logger.exception("Unexpected error while streaming query results.")
        yield b'{"error":"Internal query error."}\n'


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
