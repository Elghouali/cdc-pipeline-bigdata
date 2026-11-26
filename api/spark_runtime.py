"""Discover live per-layer Spark driver REST endpoints in Kubernetes mode."""

import asyncio
import os

import httpx


def driver_urls() -> dict[str, str]:
    if os.getenv("SPARK_MODE") != "local-pods":
        return {}
    return {
        layer: f"http://cdc-spark-{layer}:4040" for layer in ("bronze", "silver", "gold")
    }


async def live_applications(client: httpx.AsyncClient) -> dict[str, list[dict]]:
    async def fetch(layer, url):
        try:
            response = await client.get(f"{url}/api/v1/applications")
            response.raise_for_status()
            body = response.json()
            apps = body if isinstance(body, list) else []
            return layer, [
                app
                for app in apps
                if isinstance(app, dict)
                and any(
                    not attempt.get("completed", True)
                    for attempt in app.get("attempts", [])
                )
            ]
        except (httpx.HTTPError, ValueError):
            return layer, []

    return dict(
        await asyncio.gather(*(fetch(layer, url) for layer, url in driver_urls().items()))
    )
