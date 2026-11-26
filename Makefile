.PHONY: up dev down reset test lint logs status help \
        generate-configs check-env \
        frontend-install frontend-dev \
        spark-bronze spark-silver spark-gold \
        connector-register simulate \
        api-shell trino-shell postgres-shell

# ── Load .env ──────────────────────────────────────────────────────────────────
ifneq (,$(wildcard .env))
  include .env
  export
endif

COMPOSE      := docker compose
DEV_COMPOSE  := docker compose -f docker-compose.yml -f docker-compose.dev.yml

# ── Primary targets ────────────────────────────────────────────────────────────

up: check-env generate-configs          ## Start all services (production config)
	$(COMPOSE) up -d
	@echo ""
	@echo "CDC Pipeline is running. Access points:"
	@echo "  Spark Master UI  → http://localhost:8085"
	@echo "  Trino UI         → http://localhost:8080"
	@echo "  MinIO Console    → http://localhost:9001"
	@echo "  Superset         → http://localhost:8088"
	@echo "  Kafka Connect    → http://localhost:8083"
	@echo "  Frontend         → http://localhost:3000"
	@echo "  API              → http://localhost:8000"
	@echo "  Grafana          → http://localhost:3001"
	@echo ""

dev: check-env generate-configs         ## Start all services (dev config, hot-reload)
	$(DEV_COMPOSE) up -d
	@echo "Dev stack is up (hot-reload enabled)."

down:                                   ## Stop all services (keep volumes)
	$(COMPOSE) down

reset:                                  ## Stop all services and DELETE all volumes
	@echo "WARNING: This will delete all pipeline data. Press Ctrl+C to abort."
	@sleep 3
	$(COMPOSE) down -v --remove-orphans
	@echo "Reset complete. Run 'make up' to start fresh."

logs:                                   ## Follow all service logs
	$(COMPOSE) logs -f

status:                                 ## Show service health/status
	$(COMPOSE) ps

# ── Config generation ──────────────────────────────────────────────────────────

generate-configs:                       ## Render config templates with env vars
	@bash scripts/generate_configs.sh

check-env:                              ## Validate .env has all required keys
	@bash scripts/check_env.sh

# ── Testing & Linting ──────────────────────────────────────────────────────────

test: test-python test-frontend test-shell  ## Run all tests

test-python:                            ## Run Python unit tests
	@echo "── Python tests ─────────────────────────────────────"
	@if [ -d api ]; then \
	  cd api && python -m pytest tests/ -v --tb=short; \
	else \
	  echo "API directory not found."; \
	fi

test-frontend:                          ## Run frontend unit tests (Vitest)
	@echo "── Frontend tests ───────────────────────────────────"
	@if [ -d frontend ]; then \
	  cd frontend && npm run test; \
	else \
	  echo "Frontend directory not found."; \
	fi

test-shell:                             ## Lint shell scripts with shellcheck
	@echo "── Shell script checks ──────────────────────────────"
	@if command -v shellcheck >/dev/null 2>&1; then \
	  shellcheck scripts/*.sh; \
	else \
	  echo "shellcheck not installed — skipping."; \
	fi

test-e2e:                               ## Run Playwright E2E tests
	@if [ -d frontend ]; then \
	  cd frontend && npx playwright test 2>&1 || true; \
	else \
	  echo "Frontend not yet created (Phase 3)."; \
	fi

lint: lint-python lint-frontend lint-shell  ## Run all linters

lint-python:                            ## Lint Python with ruff
	@if command -v ruff >/dev/null 2>&1; then \
	  ruff check spark_jobs/ $(shell [ -d api ] && echo api/); \
	else \
	  echo "ruff not installed — run: pip install ruff"; \
	fi

lint-frontend:                          ## Lint TypeScript with ESLint + type check
	@if [ -d frontend ]; then \
	  cd frontend && npm run lint && npm run type-check; \
	else \
	  echo "Frontend directory not found."; \
	fi

lint-shell:                             ## Lint shell scripts with shellcheck
	@if command -v shellcheck >/dev/null 2>&1; then \
	  shellcheck scripts/*.sh; \
	fi

frontend-install:                       ## Install frontend npm dependencies
	@if [ -d frontend ]; then \
	  cd frontend && npm install; \
	else \
	  echo "Frontend directory not found."; \
	fi

frontend-dev:                           ## Start frontend dev server locally (no Docker)
	@if [ -d frontend ]; then \
	  cd frontend && npm run dev; \
	else \
	  echo "Frontend directory not found."; \
	fi

# ── Spark job submission ───────────────────────────────────────────────────────

spark-bronze:                           ## Start supervised Bronze driver
	$(COMPOSE) exec -d spark-master python3 /opt/spark-apps/supervise.py bronze

spark-silver:                           ## Start supervised Silver driver
	$(COMPOSE) exec -d spark-master python3 /opt/spark-apps/supervise.py silver

GOLD_REFRESH_SECONDS ?= 300
spark-gold:                             ## Start supervised Gold driver
	$(COMPOSE) exec -d spark-master python3 /opt/spark-apps/supervise.py gold --interval-seconds $(GOLD_REFRESH_SECONDS)

spark-all:                              ## Start all drivers after bounded readiness checks
	$(MAKE) spark-bronze
	python3 scripts/wait_tables.py bronze
	$(MAKE) spark-silver
	python3 scripts/wait_tables.py silver
	$(MAKE) spark-gold

spark-status:                           ## Show supervisor state (one JSON line per layer)
	$(COMPOSE) exec -T spark-master python3 /opt/spark-apps/supervise.py --status

reconcile:                              ## Compare source and Silver active key sets (quiescent source)
	python3 scripts/reconcile.py

# ── Pipeline operations ────────────────────────────────────────────────────────

connector-register:                     ## Register Debezium CDC connector
	@bash scripts/register_connector.sh

connector-status:                       ## Show Debezium connector status
	@curl -s http://localhost:8083/connectors/cdc-postgres/status | python3 -m json.tool

simulate:                               ## Start e-commerce data simulator (background)
	@bash scripts/simulate_changes.sh &
	@echo "Data simulator started in background"

pipeline-start: up                      ## Full pipeline startup (one command)
	$(MAKE) connector-register
	$(MAKE) spark-all
	$(MAKE) simulate

# ── Interactive shells ─────────────────────────────────────────────────────────

api-shell:                              ## Open shell in API container
	$(COMPOSE) exec api bash 2>/dev/null || echo "API not yet created (Phase 2)."

trino-shell:                            ## Open Trino CLI
	$(COMPOSE) exec trino trino

postgres-shell:                         ## Open psql shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-postgres} -d ecommerce

kafka-topics:                           ## List Kafka topics
	$(COMPOSE) exec kafka kafka-topics --bootstrap-server localhost:9092 --list

restart-%:                              ## Restart a specific service: make restart-kafka
	$(COMPOSE) restart $*

# ── Help ───────────────────────────────────────────────────────────────────────

help:                                   ## Show this help
	@echo ""
	@echo "CDC Pipeline — Make Targets"
	@echo "─────────────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'
	@echo ""

.DEFAULT_GOAL := help
