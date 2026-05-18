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
    CMD curl -sf http://localhost:8000/ || exit 1

# ── dev: hot-reload for local development ──────
FROM base AS dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── prod: multi-worker production server ───────
FROM base AS prod
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
