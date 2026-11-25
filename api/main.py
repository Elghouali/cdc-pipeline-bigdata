"""FastAPI application entrypoint for the CDC pipeline API service.

Run via uvicorn (see api/Dockerfile). Imported by api/tests/test_health.py.
Wires CORS, the database lifespan, and all feature routers.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from db import connect, disconnect, init_schema
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import alerts, auth, connector, events, health, metrics, query, spark

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("cdc-api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Open the DB pool and ensure schema exists; clean up on shutdown."""
    logger.info("Starting CDC API service.")
    settings.validate_security()
    try:
        await connect()
        await init_schema()
    except Exception:
        logger.exception("Startup failed while initializing the database.")
        raise
    yield
    await disconnect()
    logger.info("CDC API service stopped.")


app = FastAPI(
    title="CDC Pipeline API",
    description="Backend API for the Medallion Architecture CDC pipeline console.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Convert uncaught exceptions into a consistent {"detail": ...} body."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    """Service banner with a pointer to the OpenAPI docs."""
    return {"service": "cdc-pipeline-api", "version": "1.0.0", "docs": "/docs"}


app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(query.router)
app.include_router(events.router)
app.include_router(spark.router)
app.include_router(connector.router)
app.include_router(auth.router)
app.include_router(alerts.router)
