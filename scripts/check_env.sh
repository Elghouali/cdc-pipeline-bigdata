#!/usr/bin/env bash
# Validates that all required environment variables are present in .env
# Called by: make check-env (runs before make up / make dev)
set -euo pipefail

REQUIRED_KEYS=(
  POSTGRES_USER
  POSTGRES_PASSWORD
  MINIO_ROOT_USER
  MINIO_ROOT_PASSWORD
  MARIADB_ROOT_PASSWORD
  MARIADB_HIVE_PASSWORD
  SUPERSET_SECRET_KEY
  SUPERSET_ADMIN_PASSWORD
)

ENV_FILE="${1:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found."
  echo "       Copy .env.example to .env and fill in the values:"
  echo "       cp .env.example .env"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

missing=()
for key in "${REQUIRED_KEYS[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    missing+=("$key")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: Missing required variables in $ENV_FILE:"
  for m in "${missing[@]}"; do
    echo "  - $m"
  done
  echo ""
  echo "See .env.example for reference."
  exit 1
fi

echo "OK: All required environment variables are present."
