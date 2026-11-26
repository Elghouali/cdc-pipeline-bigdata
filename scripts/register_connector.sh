#!/usr/bin/env bash
# Update connector configuration without deleting the connector or its offsets.
set -euo pipefail
CONNECT_URL=${CONNECT_URL:-http://localhost:8083}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."
CONNECTOR_NAME=cdc-postgres
for i in $(seq 1 30); do
  if curl -fsS --max-time 5 "${CONNECT_URL}/connectors" >/dev/null 2>&1; then
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "Kafka Connect is unavailable" >&2
    exit 1
  fi
  sleep 5
done

# Read the password from the container environment, quoted by psql.
docker compose exec -T postgres sh -c 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d ecommerce' <<'SQL'
\getenv password DEBEZIUM_PASSWORD
ALTER ROLE debezium PASSWORD :'password';
SQL

python3 -c 'import json; print(json.dumps(json.load(open("config/debezium-connector.json"))["config"]))' |
  curl -fsS --max-time 60 -X PUT "${CONNECT_URL}/connectors/${CONNECTOR_NAME}/config" \
    -H "Content-Type: application/json" --data-binary @- >/dev/null

for i in $(seq 1 24); do
  if curl -fsS --max-time 5 "${CONNECT_URL}/connectors/${CONNECTOR_NAME}/status" |
    python3 -c 'import json,sys; s=json.load(sys.stdin); tasks=s.get("tasks", []); sys.exit(not (s["connector"]["state"]=="RUNNING" and tasks and all(t["state"]=="RUNNING" for t in tasks)))'; then
    echo "Connector and all tasks are RUNNING"
    exit 0
  fi
  sleep 5
done
echo "Connector or task did not become RUNNING" >&2
exit 1
