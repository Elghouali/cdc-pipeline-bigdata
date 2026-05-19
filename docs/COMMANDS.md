# CDC Pipeline — Command Reference

All commands in the order you need them to go from zero to a fully running pipeline.

---

## Prerequisites

| Tool | Min version | Install |
|------|-------------|---------|
| Docker Desktop | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled) | bundled with Docker Desktop |
| Git | any | https://git-scm.com |
| Node.js | 20+ | https://nodejs.org (only for local frontend dev) |
| Python | 3.11+ | https://python.org (only for local API dev) |
| make | any | bundled on Linux/Mac; `winget install GnuWin32.Make` on Windows |

---

## 1. First-time Setup

```bash
# 1-a. Clone the repository
git clone <repo-url>
cd cdc-pipeline

# 1-b. Create your environment file from the template
cp .env.example .env

# 1-c. Open .env and fill in every value — none are optional.
#      Required keys:
#        POSTGRES_USER / POSTGRES_PASSWORD
#        MINIO_ROOT_USER / MINIO_ROOT_PASSWORD
#        MARIADB_ROOT_PASSWORD / MARIADB_HIVE_PASSWORD
#        SUPERSET_SECRET_KEY / SUPERSET_ADMIN_PASSWORD
#        API_SECRET_KEY        (generate: openssl rand -hex 32)
#        API_ADMIN_PASSWORD
#        GRAFANA_ADMIN_PASSWORD
```

---

## 2. Start the Full Stack

```bash
# Validates .env, renders config templates, then starts all Docker services
make up
```

Wait approximately **60–90 seconds** for all services to initialise before proceeding.

```bash
# Check that every container is healthy
make status

# Watch all logs in real time (Ctrl+C to exit)
make logs
```

### Access points after `make up`

| Service | URL | Login |
|---------|-----|-------|
| **Frontend** (Control Plane) | http://localhost:3000 | `admin` / `API_ADMIN_PASSWORD` |
| **API** (OpenAPI docs) | http://localhost:8000/docs | — |
| **Trino UI** | http://localhost:8080 | — |
| **Spark Master UI** | http://localhost:8085 | — |
| **MinIO Console** | http://localhost:9001 | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` |
| **Superset** | http://localhost:8088 | `admin` / `SUPERSET_ADMIN_PASSWORD` |
| **Kafka Connect** | http://localhost:8083 | — |
| **Grafana** | http://localhost:3001 | `admin` / `GRAFANA_ADMIN_PASSWORD` |
| **Prometheus** | http://localhost:9090 | — |
| **Alertmanager** | http://localhost:9093 | — |

---

## 3. Activate the CDC Pipeline

Run these three steps in order after `make up`.

### Step 1 — Register the Debezium connector

```bash
make connector-register
```

Registers `config/debezium-connector.json` with Kafka Connect and polls until
the connector reaches `RUNNING` state. On success it prints the six CDC topic names.

```bash
# Verify at any time
make connector-status
```

### Step 2 — Submit Spark streaming jobs

```bash
# Submit all three jobs in sequence: Bronze → Silver → Gold
make spark-all

# Or individually:
make spark-bronze   # Kafka → Bronze Iceberg (raw events)
make spark-silver   # Bronze → Silver Iceberg (dedup + type-cast)
make spark-gold     # Silver → Gold Iceberg (business aggregations, 5-min refresh)
```

Confirm the jobs appear as running applications at http://localhost:8085.

### Step 3 — Start the data simulator (optional)

```bash
# Generates continuous e-commerce events in the background
make simulate
```

---

## 4. One-command Full Start

If `.env` exists and images are already pulled, run everything in one shot:

```bash
make pipeline-start
```

Equivalent to: `make up` → `make connector-register` → `make spark-all` → `make simulate`

---

## 5. Development Workflow

### Hot-reload dev stack (Docker)

```bash
make dev
```

Mounts source directories into the containers so changes to `api/` and
`spark_jobs/` take effect without rebuilding images.

### Frontend local dev server (fastest UI iteration)

```bash
# First time only
make frontend-install     # runs: cd frontend && npm install

# Start Vite on http://localhost:3000
make frontend-dev         # runs: cd frontend && npm run dev
```

The Vite dev server proxies `/api` and `/auth` to `http://localhost:8000`,
so the Docker API must be running (`make up` or `docker compose up -d api`).

### API local dev server

```bash
cd api

# Create and activate a virtual environment
python -m venv .venv

source .venv/bin/activate          # Linux / Mac
.venv\Scripts\Activate.ps1         # Windows PowerShell

pip install -r requirements.txt

# Start with auto-reload
uvicorn main:app --reload
```

---

## 6. Testing & Linting

```bash
# Run all test suites
make test

# Individual suites
make test-python      # pytest  — api/tests/
make test-frontend    # Vitest  — frontend/src/
make test-shell       # shellcheck — scripts/*.sh
make test-e2e         # Playwright — frontend/tests/e2e/

# Run all linters
make lint

# Individual linters
make lint-python      # ruff
make lint-frontend    # ESLint + tsc --noEmit
make lint-shell       # shellcheck
```

---

## 7. Interactive Shells & Useful Queries

```bash
make api-shell        # bash inside the running API container
make trino-shell      # Trino CLI (run SQL against Iceberg tables)
make postgres-shell   # psql against the source database
make kafka-topics     # list all Kafka topics
```

### Key Trino queries

```sql
-- Row counts across all Iceberg tables
SELECT table_schema, table_name
FROM iceberg.information_schema.tables
WHERE table_schema = 'analytics'
ORDER BY table_name;

-- Latest Gold sales facts
SELECT *
FROM iceberg.analytics.gold_sales_facts
ORDER BY sale_date DESC
LIMIT 20;

-- Revenue by channel (last 30 days)
SELECT channel, SUM(gross_revenue) AS revenue
FROM iceberg.analytics.gold_sales_facts
WHERE sale_date >= current_date - interval '30' day
GROUP BY channel
ORDER BY revenue DESC;

-- Payment method breakdown
SELECT method, SUM(total_amount) AS total
FROM iceberg.analytics.gold_payments_summary
GROUP BY method
ORDER BY total DESC;
```

---

## 8. Restart a Single Service

```bash
# Pattern: make restart-<service-name>
make restart-kafka
make restart-kafka-connect
make restart-spark-master
make restart-trino
make restart-api
make restart-frontend
```

---

## 9. Stop the Stack

```bash
# Stop containers, keep all data volumes
make down

# Stop containers AND delete all volumes (full wipe)
make reset
```

> `make reset` permanently deletes all Iceberg tables, Kafka offsets,
> and PostgreSQL data. There is a 3-second abort window.

---

## 10. Quick-reference Card

```
FIRST TIME
  cp .env.example .env          # copy env template
  nano .env                     # fill in passwords
  make up                       # start all services (~90s)
  make connector-register       # activate CDC connector
  make spark-all                # start Bronze/Silver/Gold jobs
  make simulate                 # generate test data

DAILY USE
  make up                       # start the stack
  make status                   # check container health
  make logs                     # tail all service logs
  make down                     # stop (data preserved)

DEVELOPMENT
  make dev                      # hot-reload Docker stack
  make frontend-dev             # Vite UI dev server
  make test                     # run all tests
  make lint                     # run all linters

EMERGENCY
  make reset                    # wipe everything and start fresh
  make restart-<service>        # restart one container
```

---

## Service Dependency Order

Docker Compose resolves this automatically, but useful to know when
troubleshooting startup failures:

```
PostgreSQL ──────────────────────────────────┐
  └── Kafka Connect (Debezium)                │
        └── Kafka ←── Zookeeper              │
              └── Bronze Spark job           │
                    └── Silver Spark job     │
                          └── Gold Spark job │
                                             │
MinIO ←── minio-init (bucket setup)          │
  └── Hive Metastore ←── MariaDB             │
        └── Spark jobs (write Iceberg)       │
              └── Trino (query Iceberg) ─────┘
                    └── API (proxy layer)
                          └── Frontend
```
