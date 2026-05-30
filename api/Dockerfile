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
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
