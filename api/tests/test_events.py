"""Security regression tests for the CDC event endpoint."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.events import _decode_envelope, _to_event, router


def test_stream_rejects_missing_or_invalid_token():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client, patch("routers.events.AIOKafkaConsumer") as consumer:
        assert client.get("/api/events/stream").status_code == 401
        assert (
            client.get(
                "/api/events/stream", headers={"Authorization": "Bearer invalid"}
            ).status_code
            == 401
        )
        consumer.assert_not_called()


def test_metadata_only_for_all_operations():
    for op in ("c", "u", "d", "r"):
        event = _to_event(
            "cdc.public.customers",
            {
                "op": op,
                "source": {"table": "unexpected"},
                "ts_ms": 123,
                "before": {"email": "private@example.invalid"},
                "after": {"name": "Private", "amount": 500},
            },
        )
        assert event == {
            "topic": "cdc.public.customers",
            "op": op,
            "table": "customers",
            "ts": 123,
            "payload": {},
        }


def test_rejects_non_object_json():
    assert _decode_envelope(b"[]") is None
    assert _decode_envelope(b"null") is None
    assert _decode_envelope(b"invalid") is None
