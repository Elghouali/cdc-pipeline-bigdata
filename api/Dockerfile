# ─────────────────────────────────────────────
#  CDC Pipeline API — multi-stage image
#  Stages: base -> dev | prod
# ─────────────────────────────────────────────

# ── base: shared runtime + dependencies ───────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# ── dev: hot-reload for local development ──────
FROM base AS dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── prod: single async worker ─────────────────
# Multiple workers would each maintain a separate in-process cache (_cache in
# metrics.py), causing up to N× more Trino queries than expected. A single
# async worker handles high concurrency correctly via asyncio. To scale
# horizontally, run multiple containers behind a load balancer and replace
# the in-process cache with a shared Redis instance.
FROM base AS prod
# Neither setuptools nor wheel is required to run the installed wheels.
# Removing the build tool also removes its vulnerable vendored dependencies.
RUN python -m pip uninstall -y setuptools wheel \
    && python -m pip check \
    && python -c "import fastapi, uvicorn, asyncpg, aiokafka, passlib, bcrypt, jwt"
RUN groupadd --gid 10001 cdc && useradd --uid 10001 --gid 10001 --no-create-home cdc
USER 10001:10001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
