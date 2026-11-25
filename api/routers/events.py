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
from fastapi import APIRouter, Request
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
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _to_event(topic: str, envelope: dict[str, Any]) -> dict[str, Any]:
    """Map a Debezium envelope to the public SSE event shape."""
    source = envelope.get("source") or {}
    op = envelope.get("op", "r")
    table = source.get("table") or topic.split(".")[-1]
    ts = envelope.get("ts_ms") or source.get("ts_ms")
    payload = envelope.get("after") if op != "d" else envelope.get("before")
    return {
        "topic": topic,
        "op": op,
        "table": table,
        "ts": ts,
        "payload": payload or {},
    }


async def _event_generator(request: Request) -> AsyncIterator[bytes]:
    # Each SSE connection gets a unique group_id so every browser tab receives
    # all events. A shared group_id would cause Kafka to load-balance messages
    # across connections, meaning each tab sees only a fraction of events.
    unique_group = f"{settings.kafka_consumer_group}-{uuid.uuid4().hex}"
    consumer = AIOKafkaConsumer(
        *CDC_TOPICS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=unique_group,
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    try:
        await consumer.start()
    except KafkaError as exc:
        logger.error("Kafka consumer failed to start: %s", exc)
        yield _sse("error", {"detail": f"Kafka unavailable: {exc}"})
        return

    yield _sse("ready", {"topics": list(CDC_TOPICS)})
    logger.info("SSE client connected; streaming CDC events.")

    last_heartbeat = time.monotonic()

    try:
        while True:
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
                    envelope = _decode_envelope(message.value)
                    if envelope is None:
                        continue
                    yield _sse("change", _to_event(tp.topic, envelope))
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled by server shutdown.")
        raise
    except KafkaError as exc:
        logger.error("Kafka error during streaming: %s", exc)
        yield _sse("error", {"detail": str(exc)})
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped.")


@router.get("/stream")
async def stream_events(request: Request) -> StreamingResponse:
    """Stream live CDC change events to the client over SSE."""
    return StreamingResponse(
        _event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
