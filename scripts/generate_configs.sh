#!/usr/bin/env bash
# Renders config templates (*.template) into actual config files using envsubst.
# Called by: make generate-configs (runs before make up / make dev)
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
export MARIADB_HIVE_PASSWORD="${MARIADB_HIVE_PASSWORD:-hive}"
export MARIADB_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-rootpass}"
export SUPERSET_SECRET_KEY="${SUPERSET_SECRET_KEY:-change_me_in_production}"

generate() {
  local template="$1"
  local output="$2"
  if [[ ! -f "$template" ]]; then
    echo "WARN: Template not found: $template"
    return
  fi
  envsubst < "$template" > "$output"
  echo "  Generated: $output"
}

echo "Generating configs from templates..."
generate config/spark/spark-defaults.conf.template         config/spark/spark-defaults.conf
generate config/trino/catalog/iceberg.properties.template  config/trino/catalog/iceberg.properties
generate config/hive/hive-site.xml.template                config/hive/hive-site.xml
echo "Done."
