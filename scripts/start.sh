#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  start.sh — Full CDC pipeline startup sequence
#
#  1. Validate environment and render config templates
#  2. Start all Docker Compose services
#  3. Wait for critical services (Postgres, Kafka, Connect, Hive, Trino)
#  4. Register the Debezium connector
#  5. Submit Spark streaming jobs (Bronze → Silver → Gold)
#  6. Start the traffic simulator in the background
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_DIR"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓  $*"; }
fail() { echo "[$(date '+%H:%M:%S')] ✗  $*" >&2; exit 1; }

SIM_PID=""

cleanup() {
  if [[ -n "$SIM_PID" ]]; then
    log "Caught signal — stopping simulator (PID ${SIM_PID}) …"
    kill "${SIM_PID}" 2>/dev/null || true
  fi
  log "Shutdown complete."
}
trap cleanup EXIT INT TERM

# ── Health check helpers ───────────────────────────────────────────────────────

wait_http() {
  local name="$1" url="$2" retries="${3:-60}" delay="${4:-5}"
  log "Waiting for ${name} (${url}) …"
  for i in $(seq 1 "$retries"); do
    if curl -sf "$url" > /dev/null 2>&1; then
      ok "${name} ready (attempt ${i})"
      return 0
    fi
    sleep "$delay"
  done
  fail "${name} did not respond after $((retries * delay))s"
}

wait_postgres() {
  local retries=60
  local pg_user="${POSTGRES_USER:-postgres}"
  local pg_db="${PGDATABASE:-ecommerce}"
  log "Waiting for PostgreSQL …"
  for i in $(seq 1 "$retries"); do
    if docker exec cdc-postgres pg_isready -U "${pg_user}" -d "${pg_db}" > /dev/null 2>&1; then
      ok "PostgreSQL ready (attempt ${i})"
      return 0
    fi
    sleep 5
  done
  fail "PostgreSQL not ready"
}

wait_kafka() {
  local retries=40
  log "Waiting for Kafka broker …"
  for i in $(seq 1 "$retries"); do
    if docker exec cdc-kafka \
        kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
      ok "Kafka ready (attempt ${i})"
      return 0
    fi
    sleep 5
  done
  fail "Kafka not ready"
}

wait_hive_metastore() {
  local retries=60
  log "Waiting for Hive Metastore (port 9083) …"
  for i in $(seq 1 "$retries"); do
    # Use bash /dev/tcp instead of nc — netcat is not installed in apache/hive.
    if docker exec cdc-hive-metastore bash -c \
        'exec 3<>/dev/tcp/localhost/9083 && exec 3>&-' 2>/dev/null; then
      ok "Hive Metastore ready (attempt ${i})"
      return 0
    fi
    sleep 5
  done
  fail "Hive Metastore not ready"
}

# ── Spark job submitter ────────────────────────────────────────────────────────

spark_submit() {
  local job="$1"
  log "spark-submit: ${job} …"
  local layer="${job%_job.py}"
  docker exec -d cdc-spark-master sh -c '
    exec /opt/spark/bin/spark-submit --master spark://spark-master:7077 \
      --deploy-mode client --conf spark.executor.memory=1g --conf spark.executor.cores=2 --conf spark.cores.max=2 \
      "/opt/spark-apps/$1" > "/tmp/cdc-$2.log" 2>&1
  ' cdc-driver "$job" "$layer"
  ok "${job} submitted (driver log: /tmp/cdc-${layer}.log in spark-master)"
}

# ─────────────────────────────────────────────────────────────────────────────
log "═══════════════════════════════════════════════"
log "  CDC Pipeline — Full Startup"
log "═══════════════════════════════════════════════"

# ── Pre-flight: validate env and generate configs ─────────────────────────────
log "Pre-flight — validating environment …"
bash "${SCRIPT_DIR}/check_env.sh"
log "Pre-flight — rendering config templates …"
bash "${SCRIPT_DIR}/generate_configs.sh"
ok "Pre-flight complete."

# ── Step 1: Bring up all services ─────────────────────────────────────────────
log "Step 1/5 — docker compose up …"
docker compose up -d --build --remove-orphans
ok "All containers started."

# ── Step 2: Wait for services ─────────────────────────────────────────────────
log "Step 2/5 — Waiting for service readiness …"
wait_postgres
wait_kafka
wait_http  "Kafka Connect"  "http://localhost:8083/connectors"        60 5
wait_hive_metastore
wait_http  "MinIO"          "http://localhost:9000/minio/health/live" 30 5
wait_http  "Trino"          "http://localhost:8080/v1/status"         60 5
ok "All services healthy."

# ── Step 3: Register Debezium connector ───────────────────────────────────────
log "Step 3/5 — Registering Debezium connector …"
bash "${SCRIPT_DIR}/register_connector.sh"

# Wait for Debezium initial snapshot to reach Kafka before Spark starts
log "Pausing 20s for Debezium initial snapshot …"
sleep 20

# ── Step 4: Submit Spark streaming jobs ───────────────────────────────────────
log "Step 4/5 — Submitting Spark jobs …"
spark_submit "bronze_job.py"
sleep 10   # let Bronze create Iceberg tables before Silver reads them
spark_submit "silver_job.py"
sleep 10
spark_submit "gold_job.py"
ok "All Spark jobs submitted."

# ── Step 5: Start traffic simulator ───────────────────────────────────────────
log "Step 5/5 — Starting CDC traffic simulator …"
bash "${SCRIPT_DIR}/simulate_changes.sh" 5 &
SIM_PID=$!
ok "Traffic simulator running (PID ${SIM_PID})"

# ─────────────────────────────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════"
log "  Pipeline is LIVE"
log "═══════════════════════════════════════════════"
log ""
log "  UI endpoints:"
log "    Spark Master    http://localhost:8085"
log "    MinIO Console   http://localhost:9001   ${MINIO_ROOT_USER:-minioadmin} / ***"
log "    Trino UI        http://localhost:8080"
log "    Superset        http://localhost:8088   admin / ***"
log "    Kafka Connect   http://localhost:8083"
log ""
log "  Kafka topics:"
log "    cdc.public.customers   cdc.public.products"
log "    cdc.public.orders      cdc.public.order_items"
log "    cdc.public.payments    cdc.public.returns"
log ""
log "  Iceberg tables (iceberg.analytics.*):"
log "    bronze_*_cdc   silver_*   gold_*"
log ""
log "  Useful commands:"
log "    docker logs -f cdc-spark-master     # Spark job output"
log "    docker logs -f cdc-kafka-connect    # Debezium connector"
log "    docker compose down -v              # Stop and clean up"
log ""
log "  Simulator PID: ${SIM_PID}  (Ctrl-C to stop)"
log "═══════════════════════════════════════════════"

# Keep alive so the trap fires cleanly on Ctrl-C / SIGTERM.
wait $SIM_PID
