# CDC Pipeline — Enterprise-Scale Improvement Plan

> **Purpose:** This document lists every planned improvement task before execution.
> Review, reorder, or cut tasks here before any code is written.
>
> **Audience:** Engineering team / stakeholder review.
> **Date:** 2026-05-18
> **Current state:** Single Docker Compose stack, no frontend, no CI/CD, no monitoring.

---

## Executive Summary

The pipeline already has a solid medallion lakehouse core (PostgreSQL → Debezium → Kafka → Spark → Iceberg → Trino → Superset). To reach **enterprise grade** it needs:

1. A **React-based operational dashboard** (replace/supplement Superset with a custom UI)
2. **Observability** (metrics, alerting, tracing, data-quality checks)
3. **CI/CD & GitOps** (automated test, build, deploy)
4. **Security hardening** (secrets management, RBAC, TLS)
5. **Production-grade infrastructure** (Kubernetes manifests, Helm chart, cloud-ready)
6. **Data governance** (schema registry, lineage, SLA contracts)
7. **Developer experience** (hot-reload, local dev parity, documentation site)

---

## Task List

Tasks are grouped by domain. Each task has a **Priority** (`P0`=must-have, `P1`=high, `P2`=medium, `P3`=nice-to-have) and an **Effort** estimate (S=hours, M=1-2 days, L=3-5 days, XL=week+).

---

### DOMAIN 1 — Frontend Layer (Custom React Dashboard)

> Goal: Replace static Superset with a live, enterprise-quality operational UI that engineers, analysts, and business users can all use.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| F-01 | **Bootstrap React + TypeScript app** with Vite, Tailwind CSS 4, shadcn/ui component library | P0 | S | `frontend/` directory alongside existing pipeline. Vite dev server proxies to backend API. |
| F-02 | **Design system & theme** — dark/light mode tokens, typography scale, color palette, spacing system | P0 | S | CSS custom properties in `tokens.css`. No off-the-shelf Tailwind template look. |
| F-03 | **Pipeline Health Overview page** — live card grid showing all 12 Docker services (green/yellow/red), last heartbeat, uptime | P0 | M | Polls `/api/health` every 10 s. Uses WebSocket for real-time status. |
| F-04 | **Medallion Layer Explorer** — tabbed Bronze / Silver / Gold view; table row counts, latest partition, lag metrics | P0 | M | Fetches from Trino REST API via backend proxy. |
| F-05 | **CDC Event Feed** — real-time event stream (Kafka consumer SSE endpoint) showing last 100 events with op-type badges (INSERT/UPDATE/DELETE) | P1 | M | Server-Sent Events from Node.js backend. Filterable by table. |
| F-06 | **KPI Dashboard page** — 8 business KPI charts (revenue by channel, payment mix, order status funnel, cancellation rate, return rate, segment heatmap) | P0 | L | Recharts library. Auto-refreshes every 60 s. Date-range picker. |
| F-07 | **Data Latency Monitor** — p50/p95/p99 source-to-gold latency chart (line chart, 24 h rolling window) | P1 | M | Reads from gold_sales_facts + custom latency tracking table. |
| F-08 | **Schema Browser** — searchable list of all Iceberg tables, columns, types, partition spec, snapshot history | P1 | M | Powered by Hive Metastore REST or Trino `information_schema`. |
| F-09 | **Job Monitor page** — Spark job status (running/failed/completed), last run time, records processed, error logs | P1 | M | Reads Spark History Server REST API. |
| F-10 | **Connector Status page** — Debezium connector state, lag per partition, offset map, restart button | P1 | M | Proxies Kafka Connect REST API (`/connectors/{name}/status`). |
| F-11 | **SQL Notebook** — inline Trino query editor with syntax highlighting, result table, download CSV | P2 | L | Monaco Editor + Trino HTTP API. |
| F-12 | **Alerts & Incidents page** — list of fired alerts (lag > threshold, job failure, DQ failure) with acknowledge button | P2 | M | Reads from alerts Postgres table written by monitoring backend. |
| F-13 | **Authentication UI** — login page, JWT session, role-based route guards (Admin / Analyst / Viewer) | P1 | M | React Router v6 protected routes. Token stored in httpOnly cookie. |
| F-14 | **Responsive layout & navigation** — sidebar nav, mobile drawer, breadcrumb, keyboard shortcuts | P0 | S | Part of initial scaffold. |
| F-15 | **E2E tests (Playwright)** — smoke tests for all pages: health loads, KPI charts render, login flow | P1 | M | `tests/e2e/` directory. Runs in CI. |

---

### DOMAIN 2 — Backend API Layer

> Goal: Thin Node.js (or FastAPI) service that the React frontend calls. Proxies Trino, Spark, Kafka Connect; exposes SSE for events; owns auth.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| B-01 | **Scaffold API service** — Node.js + Fastify (or Python FastAPI). OpenAPI 3.1 spec. | P0 | S | `api/` directory. Dockerized. |
| B-02 | **Health aggregation endpoint** `GET /api/health` — polls all Docker containers via Docker daemon socket or docker-compose ps | P0 | S | Returns JSON: `{service, status, uptime}[]`. |
| B-03 | **Trino proxy** `POST /api/query` — accepts SQL, runs via Trino HTTP protocol, streams results | P0 | M | Sanitize queries (read-only, no DDL). Rate-limit per user. |
| B-04 | **Metrics endpoints** `GET /api/metrics/{layer}` — row counts, partition info, lag | P1 | M | Cached 30 s in Redis. |
| B-05 | **Kafka SSE endpoint** `GET /api/events/stream` — KafkaJS consumer, pushes events as SSE | P1 | M | Consumer group `cdc-ui-consumer`. Back-pressure handled. |
| B-06 | **Spark History proxy** `GET /api/spark/jobs` — wraps Spark History REST API | P1 | S | |
| B-07 | **Kafka Connect proxy** — GET status, POST restart | P1 | S | |
| B-08 | **Auth endpoints** — POST /auth/login, POST /auth/logout, GET /auth/me | P1 | M | JWT (RS256). Users stored in Postgres `api_users` table. bcrypt passwords. |
| B-09 | **Data quality check runner** `POST /api/dq/run` — triggers custom DQ checks | P2 | M | Returns DQ report JSON. |
| B-10 | **Alerts API** — GET /api/alerts, PATCH /api/alerts/:id/ack | P2 | S | |
| B-11 | **Unit + integration tests** — Vitest or pytest, 80% coverage target | P1 | M | |

---

### DOMAIN 3 — Observability Stack

> Goal: Full-stack observability — metrics (Prometheus), dashboards (Grafana), structured logs (Loki), alerting.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| O-01 | **Add Prometheus + Grafana to docker-compose** | P0 | S | `monitoring/prometheus.yml` scrape configs. Grafana provisioned dashboards. |
| O-02 | **Kafka exporter** (danielqsj/kafka-exporter) — topic lag, partition counts, consumer group offsets | P0 | S | Exposed on port 9308. |
| O-03 | **Postgres exporter** (postgres_exporter) — connection pool, replication slot lag, table sizes | P0 | S | |
| O-04 | **Spark metrics to Prometheus** — `PrometheusServlet` in spark-defaults.conf; scrape master + workers | P1 | S | |
| O-05 | **MinIO metrics** — MinIO already exports Prometheus metrics; add scrape target | P1 | S | |
| O-06 | **Custom CDC lag metric** — Python sidecar reads Kafka consumer group lag, writes to Prometheus Pushgateway | P1 | M | |
| O-07 | **Structured logging** — Loki + Promtail scraping all container logs; Grafana log panel | P1 | M | |
| O-08 | **Grafana dashboards** — pre-built JSON for CDC Overview, Spark Streaming, Kafka Topics, Storage Usage | P1 | M | Store in `monitoring/grafana/dashboards/`. |
| O-09 | **Alertmanager rules** — lag > 60 s, job failure, DQ check failure, disk > 80%, memory > 85% | P1 | M | Routes to Slack webhook (env-configured). |
| O-10 | **Data Quality checks** — custom SQL assertions run after each Gold refresh; results written to `dq_results` table | P1 | L | Checks: null PKs, row-count regression > 20%, latency SLA breach. |
| O-11 | **OpenTelemetry tracing** — instrument Spark jobs with OTEL SDK (trace each micro-batch lifecycle) | P2 | L | |

---

### DOMAIN 4 — Security Hardening

> Goal: No plaintext secrets, network isolation, TLS everywhere, RBAC on data access.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| S-01 | **Audit & remove all hardcoded secrets** from config files — replace with `${VAR}` references | P0 | S | Scan all YML/conf files. |
| S-02 | **Complete `.gitignore`** — ensure `.env` and all credential files are covered | P0 | S | |
| S-03 | **TLS termination proxy (Caddy)** — HTTPS for all UI services (Superset, MinIO, Trino, Grafana, API) | P1 | M | Self-signed cert for dev; auto-cert for production. |
| S-04 | **Trino file-based access control** — per-table row filters and column masks for PII fields (email, name) | P1 | M | `rules.json` access control file. |
| S-05 | **Network segmentation** — split `cdc-net` into `storage-net`, `processing-net`, `api-net` | P2 | M | |
| S-06 | **Rate limiting** on API service — per-IP and per-user (100 req/min) | P1 | S | |
| S-07 | **Secret scanning in CI** — `detect-secrets` or `truffleHog` pre-commit + CI step | P1 | S | |
| S-08 | **Kafka SASL/SCRAM authentication** between broker, connect, and Spark | P2 | M | |

---

### DOMAIN 5 — CI/CD

> Goal: Every push triggers lint, test, build. Every merge to main deploys.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| C-01 | **GitHub Actions — lint & test** on every PR: ruff + pytest, ESLint + Vitest, shellcheck | P0 | M | `.github/workflows/ci.yml` |
| C-02 | **Docker image build & push** — custom API service image pushed to GHCR on merge | P1 | M | |
| C-03 | **Integration test workflow** — `docker compose up -d`, health checks, run test suite | P1 | L | |
| C-04 | **E2E tests in CI** — Playwright headless run | P1 | M | |
| C-05 | **Dependabot** — auto-PRs for base image and dependency updates | P2 | S | |
| C-06 | **Release tagging** — semantic versioning + auto-generated changelog | P2 | S | |

---

### DOMAIN 6 — Production Infrastructure (Kubernetes / Cloud-Ready)

> Goal: Convert Docker Compose to Kubernetes manifests + Helm chart.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| K-01 | **Helm chart scaffold** — `helm/cdc-pipeline` with sub-charts per component | P1 | L | |
| K-02 | **Kubernetes manifests** — Deployments, Services, PVCs, ConfigMaps, Secrets for all services | P1 | L | `k8s/` with Kustomize overlays (dev/staging/prod). |
| K-03 | **Spark on Kubernetes** — replace Bitnami standalone with `spark-on-k8s-operator` CRDs | P1 | L | |
| K-04 | **Strimzi Kafka Operator** — replace Confluent Community with Strimzi; `KafkaConnector` CRD for Debezium | P1 | L | |
| K-05 | **Resource requests & limits** on all containers | P1 | S | Required for K8s scheduling. |
| K-06 | **Ingress + cert-manager** — HTTPS Ingress with Let's Encrypt | P1 | M | |
| K-07 | **HorizontalPodAutoscaler** for Spark workers and API service | P2 | M | |
| K-08 | **PodDisruptionBudgets** for stateful services | P2 | S | |

---

### DOMAIN 7 — Data Governance

> Goal: Schema registry, data lineage, SLA contracts.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| G-01 | **Confluent Schema Registry** — register Avro/JSON schemas for all 6 Kafka topics; enforce schema compatibility | P1 | M | Add to docker-compose. |
| G-02 | **SLA definition file** `sla.yml` — Bronze < 30 s, Silver < 90 s, Gold < 6 min; alerting thresholds derived from it | P1 | S | |
| G-03 | **Iceberg maintenance jobs** — scheduled `expire_snapshots` + `remove_orphan_files` | P1 | S | Prevents small-file problem over time. |
| G-04 | **OpenLineage instrumentation** — add `openlineage-spark` JAR; emit lineage events to Marquez | P2 | M | |
| G-05 | **Data dictionary** `docs/data-dictionary.md` — auto-generated from Hive Metastore column comments | P2 | M | |

---

### DOMAIN 8 — Developer Experience

> Goal: Fast feedback loop, reproducible local setup, great documentation.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| D-01 | **Makefile** — `make up`, `make down`, `make reset`, `make test`, `make lint` | P0 | S | Single entry point for all operations. |
| D-02 | **Dev compose override** `docker-compose.dev.yml` — hot-reload mounts for Spark jobs and API service | P0 | S | |
| D-03 | **Env parity checker** — script validates `.env` has all required keys before `make up` | P0 | S | |
| D-04 | **pre-commit hooks** — ruff, black, eslint, prettier, shellcheck, detect-secrets | P1 | S | `.pre-commit-config.yaml` |
| D-05 | **Architecture diagram (Mermaid)** — updated to cover frontend, API, monitoring, governance layers | P1 | S | Embedded in README. |
| D-06 | **Troubleshooting runbook** `docs/runbook.md` — common failure modes, recovery procedures, debug SQL | P1 | M | |
| D-07 | **CONTRIBUTING.md** — branch naming, PR template, commit convention, local setup steps | P1 | S | |
| D-08 | **Docusaurus documentation site** `docs/` — architecture, runbook, API reference, data dictionary | P2 | L | |

---

### DOMAIN 9 — Pipeline Reliability & Performance

> Goal: Fault-tolerant, self-healing, performant at scale.

| # | Task | Priority | Effort | Details |
|---|------|----------|--------|---------|
| R-01 | **Spark job restart policy** — `restart: on-failure` with backoff in Docker Compose / K8s | P0 | S | |
| R-02 | **Dead Letter Queue (DLQ)** — route malformed Debezium events to `{topic}.dlq` topic | P1 | M | Prevents Bronze job crash on bad payload. |
| R-03 | **Iceberg file compaction** — scheduled `rewrite_data_files` + `rewrite_manifests` for Bronze | P1 | S | |
| R-04 | **Backpressure tuning** — document recommended `maxOffsetsPerTrigger` per table | P1 | M | |
| R-05 | **Exactly-once semantics test** — inject 1000 events, verify Silver count matches with no duplicates | P1 | M | |
| R-06 | **Connector idempotency test** — restart Debezium mid-snapshot; verify no duplicate Bronze rows | P1 | M | |
| R-07 | **Multi-worker Spark config** — document and test 2+ worker config; verify checkpoint distribution | P2 | M | |

---

## Recommended Execution Phases

```
Phase 1 — Foundation  (unblocks everything else)
  D-01  Makefile
  D-02  Dev compose override
  D-03  Env parity checker
  S-01  Secret audit & cleanup
  S-02  .gitignore hardening
  R-01  Spark restart policy

Phase 2 — Backend API  (unblocks Frontend)
  B-01  Scaffold API service (FastAPI recommended)
  B-02  Health aggregation endpoint
  B-03  Trino proxy endpoint
  B-04  Metrics endpoints
  B-05  Kafka SSE endpoint
  B-08  Auth endpoints (JWT)

Phase 3 — Frontend Core  (first visual milestone)
  F-01  Bootstrap React + Vite + Tailwind + shadcn/ui
  F-02  Design system & tokens
  F-14  Navigation layout
  F-03  Pipeline Health page
  F-04  Medallion Layer Explorer
  F-06  KPI Dashboard (8 charts)
  F-13  Auth UI

Phase 4 — Observability
  O-01  Prometheus + Grafana
  O-02  Kafka exporter
  O-03  Postgres exporter
  O-07  Loki structured logs
  O-08  Grafana dashboards
  O-09  Alertmanager rules
  O-10  Data Quality checks

Phase 5 — CI/CD
  C-01  GitHub Actions lint/test
  C-03  Integration test workflow
  C-04  E2E in CI (Playwright)
  D-04  pre-commit hooks

Phase 6 — Security
  S-03  TLS proxy (Caddy)
  S-04  Trino RBAC
  S-06  API rate limiting
  S-07  Secret scanning in CI

Phase 7 — Advanced Frontend Features
  F-05  CDC Event Feed (SSE)
  F-07  Latency Monitor
  F-08  Schema Browser
  F-09  Spark Job Monitor
  F-10  Connector Status
  F-11  SQL Notebook (Monaco)
  F-12  Alerts page
  F-15  Playwright E2E tests

Phase 8 — Governance & Infra
  G-01  Schema Registry
  G-02  SLA definition
  G-03  Iceberg maintenance jobs
  K-01  Helm chart
  K-02  K8s manifests
  K-03  Spark on K8s operator
  K-04  Strimzi Kafka operator
```

---

## Task Count Summary

| Domain | P0 | P1 | P2 | Total |
|--------|----|----|-----|-------|
| Frontend (F) | 6 | 6 | 3 | 15 |
| Backend API (B) | 4 | 6 | 1 | 11 |
| Observability (O) | 3 | 6 | 2 | 11 |
| Security (S) | 2 | 4 | 2 | 8 |
| CI/CD (C) | 1 | 3 | 2 | 6 |
| Infrastructure (K) | 0 | 6 | 2 | 8 |
| Governance (G) | 0 | 3 | 2 | 5 |
| Dev Experience (D) | 3 | 4 | 1 | 8 |
| Reliability (R) | 2 | 5 | 1 | 8 |
| **Total** | **21** | **43** | **16** | **80** |

---

## Questions to Confirm Before Phase 1

Please answer these before any code is written:

| # | Question | Recommendation |
|---|----------|----------------|
| Q1 | **Frontend framework** — React + Vite + Tailwind CSS 4 + shadcn/ui? | Yes (recommended) |
| Q2 | **Backend API language** — FastAPI (Python, aligns with PySpark codebase) or Node.js/Fastify? | FastAPI recommended |
| Q3 | **Frontend Phase 3 scope** — Health + KPI + Auth only, or also Event Feed? | Health + KPI + Auth for v1 |
| Q4 | **Deployment target for v1** — Docker Compose only, or include K8s manifests? | Docker Compose first |
| Q5 | **Monitoring** — standalone Prometheus/Grafana in this repo, or integrate with existing stack? | Standalone (recommended) |
| Q6 | **Auth method** — Simple JWT users in Postgres, or SSO (Google / Keycloak)? | Simple JWT for v1 |
| Q7 | **UI design direction** — Dark engineering theme (recommended for data pipeline UI)? | Dark luxury / engineering |
| Q8 | **Start phase** — Ready to begin Phase 1 (Foundation) now? | Awaiting your confirmation |

---

*Once you confirm the questions above (or override any recommendation), Phase 1 execution begins immediately.*
