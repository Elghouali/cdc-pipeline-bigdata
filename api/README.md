# CDC Pipeline API

FastAPI backend (Phase 2) for the Medallion Architecture CDC pipeline. It proxies
the pipeline's internal services (Trino, Kafka Connect, Spark, Kafka, Postgres)
for the React console built in Phase 3.

## Run with Docker Compose

The `api` service is wired into the root `docker-compose.yml`:

```bash
# production target
docker compose up -d api

# development target (hot reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api
```

The API listens on `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

## Run locally (without Docker)

```bash
cd api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Required environment variables (defaults shown):

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/ecommerce` |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` |
| `TRINO_URL` | `http://trino:8080` |
| `KAFKA_CONNECT_URL` | `http://kafka-connect:8083` |
| `SPARK_MASTER_URL` | `http://spark-master:8085` |
| `API_SECRET_KEY` | `change_me_secret` |
| `API_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `API_ADMIN_PASSWORD` | `admin` |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` |

## Run tests

```bash
cd api
pip install -r requirements.txt
pytest
```

`tests/test_health.py` stubs out external services, so no live backends are
needed to run the suite.

## Default credentials

On first startup the API seeds an `admin` user in the `api_users` table with the
password from `API_ADMIN_PASSWORD`. Authenticate via `POST /auth/login`.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/health` | none |
| GET | `/api/metrics/{layer}` | none |
| POST | `/api/query` | user |
| GET | `/api/events/stream` | none (SSE) |
| GET | `/api/spark/jobs` | none |
| GET | `/api/spark/running` | none |
| GET | `/api/connector/status` | none |
| POST | `/api/connector/restart` | admin |
| POST | `/auth/login` | none |
| POST | `/auth/logout` | none |
| GET | `/auth/me` | user |
| GET | `/api/alerts` | user |
| PATCH | `/api/alerts/{id}/ack` | user |
