# CDC Pipeline — Near Real-Time Medallion Lakehouse

A fully self-contained, enterprise-grade Change Data Capture pipeline that
captures row-level changes from a PostgreSQL e-commerce database, streams
them through Kafka, transforms them across three Iceberg medallion layers
with Apache Spark, and exposes everything through a custom React dashboard
backed by a FastAPI service.

Everything runs on a **single machine** with Docker Compose — no cloud
account required. A Helm chart and Kustomize manifests are included for
Kubernetes deployment.

---

## Architecture

```
PostgreSQL 15  (WAL logical replication)
      │
      │  pgoutput slot + debezium_pub publication
      ▼
Kafka Connect  +  Debezium 2.5
      │
      │  topics: cdc.public.{customers,products,orders,order_items,payments,returns}
      ▼
Apache Kafka 7.5
      │
      ├── Spark Bronze Job ──► Iceberg bronze_{entity}_cdc   (raw, append, daily)
      │                                │
      │             Spark Silver Job ◄─┘
      │                     │
      │                     ▼
      │            Iceberg silver_{entity}   (typed, MERGE INTO, daily)
      │                     │
      │             Spark Gold Job (5-min)
      │                     │
      │                     ▼
      │            Iceberg gold_*            (aggregates, snapshot_date)
      │                     │
      │              Trino 435  (SQL)
      │                     │
      ▼                     ▼
  FastAPI ◄──────────────────────────── React Dashboard
      │
      │  SSE /api/events/stream (live CDC feed)
      │  JWT auth  /auth/login · /auth/me
      │  Trino proxy  /api/query
      │  Metrics  /api/metrics/{bronze,silver,gold}
      │  Spark jobs  /api/spark/jobs
      │  Connector  /api/connector/status
      │  Alerts  /api/alerts
      │
      └── Prometheus · Grafana · Loki · Alertmanager
```

### Medallion Layers

| Layer | Table pattern | Write mode | Partition |
|-------|---------------|-----------|-----------|
| Bronze | `bronze_{entity}_cdc` (6 tables) | Append | `ingestion_date` |
| Silver | `silver_{entity}` (6 tables) | MERGE INTO (upsert by PK) | `updated_date` |
| Gold | `gold_customers`, `gold_orders`, `gold_sales_facts`, `gold_payments_summary`, `gold_returns_summary` | Overwrite partitions | `snapshot_date` |

---

## Stack

| Component | Technology |
|-----------|-----------|
| Source DB | PostgreSQL 15 |
| CDC | Debezium 2.5 + Kafka Connect |
| Streaming | Apache Kafka (Confluent 7.5) |
| Processing | Apache Spark 3.5 (Structured Streaming) |
| Table format | Apache Iceberg 1.5 |
| Object store | MinIO |
| Metastore | Hive Standalone 4.0 (MariaDB backend) |
| Query engine | Trino 435 |
| Backend API | FastAPI · asyncpg · aiokafka · PyJWT |
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS |
| Monitoring | Prometheus · Grafana · Loki · Promtail · Alertmanager |
| Reverse proxy | Caddy v2 (TLS termination) |
| Packaging | Docker Compose · Helm 3 · Kustomize |
| CI/CD | GitHub Actions |

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Docker Desktop | 24.x with Compose v2 |
| RAM allocated to Docker | 8 GB |
| Free disk space | 20 GB |
| OS | Linux, macOS, or Windows with WSL2 |

No local JVM, Python, or Node.js required.

---

## Quick Start

### 1 — Configure credentials

```bash
cp .env.example .env
# Edit .env — fill in all passwords and secret keys.
# The file is gitignored; never commit it.
```

Validate your `.env` before starting:

```bash
make check-env
```

### 2 — Render config files from templates

```bash
make generate-configs
# Produces: config/spark/spark-defaults.conf
#           config/trino/catalog/iceberg.properties
#           config/hive/hive-site.xml
```

### 3 — Start the full pipeline

```bash
bash scripts/start.sh
```

This single command does everything in order:

| Step | What happens | Typical duration |
|------|-------------|-----------------|
| Pre-flight | Validates `.env`, renders config templates | < 5 s |
| Pull & start | Docker pulls all images, starts 15 containers | 3–8 min (first run) |
| Health checks | Waits for Postgres, Kafka, Connect, Hive, Trino | 1–3 min |
| Connector | Registers the Debezium CDC connector | 30 s |
| Snapshot | Waits 20 s for Debezium initial snapshot | 20 s |
| Spark jobs | Submits Bronze → Silver → Gold (detached) | < 10 s per job |
| Simulator | Starts INSERT/UPDATE/DELETE loop (5 s interval) | immediate |

When ready you will see:

```
[HH:MM:SS] ════════════════════════════════
[HH:MM:SS]   Pipeline is LIVE
[HH:MM:SS] ════════════════════════════════
```

Press **Ctrl-C** to stop — the simulator is cleaned up automatically.

### 4 — Alternatively: use Make targets

```bash
make up              # start (production config)
make dev             # start (dev config — hot-reload for API and frontend)
make down            # stop, keep volumes
make reset           # stop and delete all volumes
```

---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **React Dashboard** | http://localhost:3000 | admin / `$API_ADMIN_PASSWORD` |
| **FastAPI docs** | http://localhost:8000/docs | JWT token from dashboard |
| Spark Master UI | http://localhost:8085 | — |
| Trino UI | http://localhost:8080 | — |
| MinIO Console | http://localhost:9001 | `$MINIO_ROOT_USER` / `$MINIO_ROOT_PASSWORD` |
| Kafka Connect | http://localhost:8083 | — |
| Grafana | http://localhost:3001 | admin / `$GRAFANA_ADMIN_PASSWORD` |
| Prometheus | http://localhost:9090 | — |
| Alertmanager | http://localhost:9093 | — |
| Superset | http://localhost:8088 | admin / `$SUPERSET_ADMIN_PASSWORD` |

> Credentials are whatever you set in `.env` — no hardcoded defaults.
> If using the Caddy reverse proxy (`security/Caddyfile`), everything is
> available under a single TLS endpoint at `https://localhost`.

---

## React Dashboard

The dashboard (`frontend/`) provides:

| Page | What it shows |
|------|--------------|
| **Overview** | KPI strip (revenue, orders, customers, returns) · Medallion row counts · Live Kafka event feed · Service health grid |
| **Bronze / Silver / Gold** | Table list with row counts and latest partition · Schema drawer per table |
| **Query Console** | Trino SQL editor with syntax highlighting · Results table · CSV export · Ctrl-Enter shortcut |
| **Event Stream** | Live SSE feed from Kafka · Search by table · Filter by topic · INSERT / UPDATE / DELETE badges |
| **Login** | JWT auth · Pipeline architecture diagram |

---

## Data Quality

`monitoring/dq_checks.py` runs after each Gold refresh and checks:

- No NULL primary keys in `silver_customers`
- `gold_customers` is non-empty
- Row-count regression < 20% vs previous run (silver + gold)

Failures are written to `pipeline_alerts` and surfaced in the dashboard Alerts page.

Run manually:

```bash
docker compose exec api python /app/monitoring/dq_checks.py
```

---

## Querying with Trino

Open a Trino CLI session:

```bash
docker exec -it cdc-trino trino --catalog iceberg --schema analytics
```

All KPI queries are in `trino/trino_queries.sql`. Quick sanity checks:

```sql
-- Bronze: CDC event counts per table
SELECT source_table, COUNT(*) AS events
FROM (
  SELECT source_table FROM bronze_customers_cdc UNION ALL
  SELECT source_table FROM bronze_orders_cdc    UNION ALL
  SELECT source_table FROM bronze_payments_cdc
)
GROUP BY source_table;

-- Silver: deduplicated, typed rows
SELECT COUNT(*) FROM silver_customers WHERE _is_deleted = false;
SELECT COUNT(*) FROM silver_orders    WHERE _is_deleted = false;

-- Gold: business aggregates (available after first 5-min cycle)
SELECT * FROM gold_orders
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM gold_orders)
LIMIT 10;
```

---

## Spark Jobs

Submit jobs individually (detached — streaming jobs run indefinitely):

```bash
make spark-bronze    # Kafka → Bronze Iceberg (append)
make spark-silver    # Bronze → Silver (MERGE INTO)
make spark-gold      # Silver → Gold (5-min aggregation)
make spark-all       # All three, with waits for table creation
```

Check output:

```bash
docker logs -f cdc-spark-master 2>&1 | grep -E "bronze|silver|gold|Batch"
```

---

## Debezium Connector

```bash
make connector-register          # register / re-register
make connector-status            # show state (RUNNING / FAILED)

# Or directly:
curl -s http://localhost:8083/connectors/cdc-postgres/status | python3 -m json.tool
```

---

## Development

Start with hot-reload for API and frontend:

```bash
make dev
```

Run tests and linters:

```bash
make test          # Python (pytest) + Frontend (Vitest) + Shell (shellcheck)
make lint          # ruff + ESLint + tsc + shellcheck
make test-python   # pytest only
make test-frontend # Vitest only
```

Run pre-commit hooks on all files:

```bash
pre-commit run --all-files
```

---

## Kubernetes Deployment

### Helm

```bash
# Render templates (dry-run)
helm template cdc helm/cdc-pipeline \
  --set postgres.password=<pg-pass> \
  --set minio.password=<minio-pass> \
  --set api.secretKey=<jwt-secret> \
  --set grafana.adminPassword=<grafana-pass>

# Install
helm upgrade --install cdc helm/cdc-pipeline \
  --namespace cdc-pipeline --create-namespace \
  --set postgres.password=<pg-pass> \
  --set minio.password=<minio-pass> \
  --set api.secretKey=<jwt-secret> \
  --set grafana.adminPassword=<grafana-pass>
```

### Kustomize

```bash
# Dev overlay (single replicas)
kubectl apply -k k8s/overlays/dev

# Prod overlay (scaled replicas, PDBs)
kubectl apply -k k8s/overlays/prod
```

---

## Project Structure

```
cdc-pipeline/
├── docker-compose.yml            15-service stack (production)
├── docker-compose.dev.yml        Dev override (hot-reload, lighter resources)
├── Makefile                      All common commands
├── .env.example                  Credential template — copy to .env
│
├── api/                          FastAPI backend service
│   ├── main.py                   App wiring (lifespan, CORS, routers)
│   ├── auth.py                   JWT utilities + FastAPI dependencies
│   ├── db.py                     asyncpg pool + schema bootstrap
│   ├── config.py                 Environment-driven settings
│   ├── trino_client.py           Async Trino HTTP client (multi-stage polling)
│   ├── models/schemas.py         Pydantic v2 request/response models
│   ├── routers/
│   │   ├── health.py             GET /api/health  (parallel service probes)
│   │   ├── metrics.py            GET /api/metrics/{layer}  (cached 30 s)
│   │   ├── query.py              POST /api/query  (read-only NDJSON stream)
│   │   ├── events.py             GET /api/events/stream  (Kafka SSE)
│   │   ├── spark.py              GET /api/spark/jobs · /running
│   │   ├── connector.py          GET /api/connector/status · POST /restart
│   │   ├── alerts.py             GET /api/alerts · PATCH /{id}/ack
│   │   └── auth.py               POST /auth/login · /logout · GET /me
│   ├── tests/                    pytest suite (5 tests)
│   ├── Dockerfile                Multi-stage (dev + prod)
│   └── requirements.txt
│
├── frontend/                     React 18 + TypeScript + Vite + Tailwind
│   ├── src/
│   │   ├── pages/                DashboardPage, LayerPage, QueryPage, StreamPage, LoginPage
│   │   ├── components/           Sidebar, TopBar, Badge, Card, Button, Spinner …
│   │   ├── lib/api.ts            Typed API client (fetch + NDJSON stream)
│   │   ├── lib/utils.ts          cn, formatNumber, parseNdjson, formatRelativeTime
│   │   ├── context/AuthContext   JWT storage, login/logout, token expiry redirect
│   │   └── types/api.ts          Shared TypeScript interfaces
│   └── vite.config.ts            Dev proxy: /api + /auth → FastAPI
│
├── spark_jobs/
│   ├── bronze_job.py             Kafka → Bronze Iceberg (streaming append)
│   ├── silver_job.py             Bronze → Silver (MERGE INTO upsert by PK)
│   └── gold_job.py               Silver → Gold (5-min aggregation, 5 tables)
│
├── sql/
│   ├── init.sql                  DDL: 6 tables + FK indexes + Debezium user + publication
│   └── seed.sql                  100 realistic Moroccan e-commerce rows per table
│
├── trino/
│   └── trino_queries.sql         8 KPI queries + 2 bonus (all with snapshot_date filter)
│
├── config/
│   ├── debezium-connector.json   Debezium source connector (name: cdc-postgres)
│   ├── spark/spark-defaults.conf.template
│   ├── trino/
│   │   ├── config.properties     query.max-memory=1GB (single-node)
│   │   ├── jvm.config
│   │   ├── node.properties
│   │   └── catalog/iceberg.properties.template
│   └── hive/hive-site.xml.template
│
├── scripts/
│   ├── start.sh                  Full pipeline startup (entry point)
│   ├── generate_configs.sh       Render .template → .conf files
│   ├── check_env.sh              Validate .env has all required keys
│   ├── register_connector.sh     POST connector to Kafka Connect REST API
│   └── simulate_changes.sh       Live INSERT / UPDATE / DELETE loop
│
├── monitoring/
│   ├── prometheus.yml            Scrape config (Kafka, Postgres, MinIO, API)
│   ├── alerts.yml                Alert rules (lag, disk, broker down, API down)
│   ├── alertmanager.yml          Slack routing (envsubst for webhook URL)
│   ├── promtail.yml              Docker log collection → Loki
│   ├── dq_checks.py              Data quality assertions → pipeline_alerts table
│   └── grafana/
│       ├── datasources/          Prometheus + Loki auto-provisioned
│       └── dashboards/           CDC Overview + Kafka Topics JSON dashboards
│
├── security/
│   ├── Caddyfile                 TLS proxy + security headers (HSTS, CSP, …)
│   ├── trino-access-control.json Column masking for silver_customers PII
│   └── rate-limit-config.json    Intended rate-limit policy (to be implemented)
│
├── helm/cdc-pipeline/            Helm chart (12 templates, values.yaml)
├── k8s/
│   ├── base/                     Kustomize base (Namespace, Postgres, Kafka, Spark, API, Frontend)
│   └── overlays/
│       ├── dev/                  Single replicas, minimal resources
│       └── prod/                 Scaled replicas, PDBs, higher limits
│
├── hive/Dockerfile               apache/hive:4.0 + MySQL JDBC + Hadoop-AWS JARs
├── .github/workflows/
│   ├── ci.yml                    Lint (ruff, shellcheck, ESLint, tsc) + test (pytest, Vitest) + Docker build
│   └── integration.yml           Full-stack integration test (weekly + on-demand)
├── .pre-commit-config.yaml       ruff, shellcheck, detect-secrets
├── Makefile                      Common developer commands
├── REPORT.md                     Full audit report (105 bugs fixed)
└── IMPROVE_PLAN.md               Original 80-task roadmap
```

---

## Source Schema

Six e-commerce tables in PostgreSQL `ecommerce.public`:

| Table | Columns |
|-------|---------|
| `customers` | id, name, email, city, segment, signup_date |
| `products` | id, name, category, brand, price, stock_qty |
| `orders` | id, order_date, customer_id, status, channel |
| `order_items` | id, order_id, product_id, quantity, unit_price |
| `payments` | id, order_id, payment_date, method, amount, status |
| `returns` | id, order_id, return_date, reason, status |

CDC is captured via a dedicated `debezium` replication user, `debezium_pub` publication, and `debezium_slot` logical replication slot.

---

## KPI Queries

All 8 KPIs are in `trino/trino_queries.sql`:

| KPI | Description | Source |
|-----|-------------|--------|
| 1 | CDC event counts by table (INSERT/UPDATE/DELETE/snapshot) | Bronze UNION ALL |
| 2 | Operation type breakdown with % share | Bronze UNION ALL |
| 3 | Source-to-analytics latency (avg, min, max, p95) | Bronze (6 tables) |
| 4 | Order status evolution — weekly | `gold_orders` |
| 5 | Total sales by period and channel | `gold_sales_facts` |
| 6 | Payment method mix by month | `gold_payments_summary` |
| 7 | Cancellation and return rates — monthly | `gold_orders` |
| 8 | Revenue by customer segment and product category | `gold_sales_facts` |

All queries filter to `snapshot_date = MAX(snapshot_date)` to avoid double-counting across daily partitions.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `make check-env` fails | Missing keys in `.env` | Fill in all values in `.env` |
| Hive Metastore restarts on first boot | Downloads MySQL JDBC driver | Wait 2 min; it is a one-time download |
| Spark S3A `Access Denied` errors | Missing MinIO credentials in generated config | Run `make generate-configs` again after updating `.env` |
| CDC connector shows `FAILED` | Debezium publication or slot missing | Check `docker logs cdc-kafka-connect`; re-run `make connector-register` |
| No rows in Silver/Gold | Bronze must run at least one batch first | Wait 60–90 s after Bronze starts |
| Gold tables empty after first 5-min cycle | Trino `iceberg.properties` misconfigured | Verify `config/trino/catalog/iceberg.properties` has correct MinIO endpoint and credentials |
| Dashboard login fails | API not reachable or wrong admin password | Check `docker logs cdc-api`; verify `API_ADMIN_PASSWORD` in `.env` |
| `make spark-bronze` returns immediately | Jobs now run detached (`-d`) by design | Check `docker logs cdc-spark-master` for streaming output |
| Docker out of memory | Docker Desktop limit too low | Increase to ≥ 8 GB in Docker Desktop → Settings → Resources |
| Slack alerts not arriving | `SLACK_WEBHOOK_URL` not set in `.env` | Add a valid webhook URL; Alertmanager uses `envsubst` at startup |

---

## First-Run Timing Reference

| Service | Typical time to healthy |
|---------|------------------------|
| PostgreSQL | 10–15 s |
| Kafka + Zookeeper | 20–30 s |
| Kafka Connect / Debezium | 30–60 s |
| Hive Metastore (schema init + JDBC download) | 60–120 s |
| Trino | 30–60 s |
| Spark (JAR download, first run only) | 2–5 min |
| Superset (pip install trino, first run) | 2–3 min |

`scripts/start.sh` waits for each service before proceeding — no manual timing needed.
