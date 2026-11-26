"""Small, bounded Prometheus endpoint for service and Spark application status."""

import asyncio
import math
import time
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from config import settings

router = APIRouter()
APP_NAMES = {
    "bronze": "cdc-bronze-ingestion",
    "silver": "cdc-silver-transform",
    "gold": "cdc-gold-aggregation",
}


async def get_json(client: httpx.AsyncClient, url: str) -> dict:
    try:
        response = await client.get(url)
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, dict) else {}
    except (httpx.HTTPError, ValueError):
        return {}


def gold_refresh_timestamp(path: Path) -> float:
    try:
        value = float(path.read_text(encoding="utf-8"))
        if math.isfinite(value) and 0 < value <= time.time():
            return value
    except (OSError, ValueError):
        pass
    return 0.0


def render_metrics(
    master: dict, connector: dict, gold_timestamp: float = 0.0
) -> str:
    apps = master.get("activeapps") or []
    tasks = connector.get("tasks") or []
    lines = [
        "# TYPE cdc_spark_master_reachable gauge",
        f"cdc_spark_master_reachable {int(bool(master))}",
        "# TYPE cdc_gold_last_success_timestamp_seconds gauge",
        f"cdc_gold_last_success_timestamp_seconds {gold_timestamp}",
        "# TYPE cdc_spark_driver_active gauge",
    ]
    for layer, name in APP_NAMES.items():
        active = sum(
            app.get("name") == name
            and app.get("state") == "RUNNING"
            and (app.get("cores") or 0) > 0
            for app in apps
        )
        lines.append(f'cdc_spark_driver_active{{layer="{layer}"}} {active}')
    running = bool(tasks) and all(task.get("state") == "RUNNING" for task in tasks)
    healthy = connector.get("connector", {}).get("state") == "RUNNING" and running
    lines.extend(
        [
            "# TYPE cdc_connector_healthy gauge",
            f"cdc_connector_healthy {int(healthy)}",
        ]
    )
    return "\n".join(lines) + "\n"


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> PlainTextResponse:
    async with httpx.AsyncClient(timeout=3.0) as client:
        master, connector = await asyncio.gather(
            get_json(client, f"{settings.spark_master_url}/json"),
            get_json(
                client,
                f"{settings.kafka_connect_url}/connectors/{settings.connector_name}/status",
            ),
        )
    return PlainTextResponse(
        render_metrics(
            master,
            connector,
            gold_refresh_timestamp(Path("/var/lib/cdc-runtime/gold-refresh")),
        ),
        media_type="text/plain; version=0.0.4",
    )
