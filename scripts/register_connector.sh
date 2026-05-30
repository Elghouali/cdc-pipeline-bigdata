#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  register_connector.sh
#  POSTs the Debezium PostgreSQL connector to the Kafka Connect REST API.
#  Idempotent: deletes any existing connector with the same name first.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONNECT_URL=${CONNECT_URL:-http://localhost:8083}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONNECTOR_CONFIG="${SCRIPT_DIR}/../config/debezium-connector.json"
CONNECTOR_NAME="cdc-postgres"
MAX_RETRIES=30
RETRY_INTERVAL=5

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Wait for Kafka Connect ───────────────────────────────────────────────────
log "Waiting for Kafka Connect at ${CONNECT_URL} …"
for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf "${CONNECT_URL}/connectors" > /dev/null 2>&1; then
    log "Kafka Connect is ready (attempt $i)."
    break
  fi
  if [[ $i -eq $MAX_RETRIES ]]; then
    log "ERROR: Kafka Connect not reachable after ${MAX_RETRIES} retries. Aborting."
    exit 1
  fi
  log "  Not ready yet — retrying in ${RETRY_INTERVAL}s … ($i/${MAX_RETRIES})"
  sleep "$RETRY_INTERVAL"
done

# ── Delete old connector if it exists ───────────────────────────────────────
# Use HTTP status code instead of python3 JSON parsing — python3 may not be
# available in all environments and the 2>/dev/null || true silently swallowed
# errors, leaving stale connectors in place.
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "${CONNECT_URL}/connectors/${CONNECTOR_NAME}" 2>/dev/null || echo "000")
if [[ "$HTTP_STATUS" == "200" ]]; then
  log "Removing existing connector '${CONNECTOR_NAME}' …"
  curl -sf -X DELETE "${CONNECT_URL}/connectors/${CONNECTOR_NAME}"
  sleep 3
  log "Removed."
fi

# ── Register connector ────────────────────────────────────────────────────────
log "Registering connector from ${CONNECTOR_CONFIG} …"
RESPONSE=$(curl -sf \
  -X POST "${CONNECT_URL}/connectors" \
  -H "Content-Type: application/json" \
  --data "@${CONNECTOR_CONFIG}")

REGISTERED=$(echo "$RESPONSE" \
  | grep -o '"name":"[^"]*"' | head -1 | sed 's/"name":"//;s/"//' 2>/dev/null || echo "ERROR")

if [[ "$REGISTERED" != "$CONNECTOR_NAME" ]]; then
  log "ERROR: Registration failed. Response:"
  echo "$RESPONSE"
  exit 1
fi
log "Connector '${REGISTERED}' registered."

# ── Poll until RUNNING ────────────────────────────────────────────────────────
log "Polling connector status …"
for i in $(seq 1 12); do
  sleep 5
  STATE=$(curl -sf "${CONNECT_URL}/connectors/${CONNECTOR_NAME}/status" 2>/dev/null \
    | grep -o '"state":"[^"]*"' | head -1 | sed 's/"state":"//;s/"//' || echo "UNKNOWN")
  log "  State: ${STATE} (check $i/12)"
  if [[ "$STATE" == "RUNNING" ]]; then
    log "Connector is RUNNING. CDC topics:"
    for t in customers products orders order_items payments returns; do
      log "  → cdc.public.${t}"
    done
    exit 0
  fi
done

log "WARNING: Connector did not reach RUNNING state within 60s."
log "Check logs with: docker logs cdc-kafka-connect"
exit 1
