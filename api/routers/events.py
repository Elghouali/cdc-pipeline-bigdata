"""Server-Sent Events router streaming live CDC changes from Kafka.

Caller: api/main.py. Endpoint: GET /api/events/stream.
Consumes Debezium change events (schemas disabled) and re-emits them as SSE.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from auth import decode_token, get_current_user, oauth2_scheme
from fastapi import APIRouter, Depends, Request
from models import User
from fastapi.responses import StreamingResponse

from config import CDC_TOPICS, settings

logger = logging.getLogger("cdc-api.events")

router = APIRouter(prefix="/api/events", tags=["events"])

_HEARTBEAT_SECONDS = 15.0


def _sse(event: str, data: dict[str, Any]) -> bytes:
    """Format a dict as an SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n".encode()


def _decode_envelope(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        envelope = json.loads(raw.decode("utf-8"))
        return envelope if isinstance(envelope, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _to_event(topic: str, envelope: dict[str, Any]) -> dict[str, Any]:
    """Publish metadata only: never forward raw before/after business records."""
    op = envelope.get("op")
    ts = envelope.get("ts_ms")
    return {
        "topic": topic,
        "op": op if op in ("c", "u", "d", "r") else "r",
        "table": topic.rsplit(".", 1)[-1],
        "ts": ts if isinstance(ts, int) and not isinstance(ts, bool) else None,
        "payload": {},
    }

async def _event_generator(
    request: Request, expires_at: float
) -> AsyncIterator[bytes]:
    # Each SSE connection gets a unique group_id so every browser tab receives
    # all events. A shared group_id would cause Kafka to load-balance messages
    # across connections, meaning each tab sees only a fraction of events.
    unique_group = f"{settings.kafka_consumer_group}-{uuid.uuid4().hex}"
    consumer = AIOKafkaConsumer(
        *CDC_TOPICS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=unique_group,
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    try:
        await consumer.start()
    except KafkaError as exc:
        logger.error("Kafka consumer failed to start: %s", exc)
        await consumer.stop()
        yield _sse("error", {"detail": "Kafka unavailable"})
        return

    yield _sse("ready", {"topics": list(CDC_TOPICS)})
    logger.info("SSE client connected; streaming CDC events.")

    last_heartbeat = time.monotonic()

    try:
        while time.time() < expires_at:
            if await request.is_disconnected():
                logger.info("SSE client disconnected.")
                break

            batch = await consumer.getmany(timeout_ms=1000, max_records=50)
            if not batch:
                now = time.monotonic()
                if now - last_heartbeat >= _HEARTBEAT_SECONDS:
                    yield b": keep-alive\n\n"
                    last_heartbeat = now
                continue

            last_heartbeat = time.monotonic()
            for tp, messages in batch.items():
                for message in messages:
                    if time.time() >= expires_at:
                        return
                    envelope = _decode_envelope(message.value)
                    if envelope is None:
                        continue
                    yield _sse("change", _to_event(tp.topic, envelope))
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled by server shutdown.")
        raise
    except KafkaError as exc:
        logger.error("Kafka error during streaming: %s", exc)
        yield _sse("error", {"detail": "Event stream unavailable"})
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped.")


@router.get("/stream")
async def stream_events(
    request: Request,
    _user: User = Depends(get_current_user),
    token: str | None = Depends(oauth2_scheme),
) -> StreamingResponse:
    """Stream authenticated, metadata-only CDC events until JWT expiry."""
    claims = decode_token(token or "")
    expires_at = min(float(claims.get("exp", 0)), time.time() + 300)
    return StreamingResponse(
        _event_generator(request, expires_at),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
