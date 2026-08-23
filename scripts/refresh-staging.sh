#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MwalimuKit — Refresh staging database from production backup
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./scripts/refresh-staging.sh /path/to/production-backup.dump.gz
#
# This drops the staging database and restores from a production
# backup. The staging database should NEVER contain real customer
# data in a way that could affect production.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <production-backup.dump.gz>" >&2
    exit 1
fi

BACKUP_FILE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.staging.yml"
ENV_FILE="$PROJECT_ROOT/.env.staging"

if [ ! -f "$ENV_FILE" ]; then
    echo "[refresh-staging] ERROR: $ENV_FILE not found" >&2
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[refresh-staging] ERROR: Backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

echo "========================================="
echo "MwalimuKit Staging Refresh"
echo "========================================="
echo ""
echo "Source:    $BACKUP_FILE"
echo "Target:    staging database (mwalimukit_staging)"
echo ""
read -p "This will DESTROY all staging data. Continue? (type 'YES' to confirm): " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi

echo "[refresh-staging] Stopping staging API..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop api || true

echo "[refresh-staging] Dropping staging database..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db psql -U mwalimu -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='mwalimukit_staging' AND pid <> pg_backend_pid();" || true
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db psql -U mwalimu -d postgres -c \
  "DROP DATABASE IF EXISTS mwalimukit_staging;"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db psql -U mwalimu -d postgres -c \
  "CREATE DATABASE mwalimukit_staging OWNER mwalimu;"

echo "[refresh-staging] Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  pg_restore -U mwalimu -d mwalimukit_staging --no-owner --role=mwalimu

echo "[refresh-staging] Running migrations on staging..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T api \
  sh -c "PYTHONPATH=/app alembic upgrade head"

echo "[refresh-staging] Starting staging API..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d api

echo "[refresh-staging] Waiting for API health..."
timeout 60 bash -c "until docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T api curl -sf http://localhost:8000/health >/dev/null 2>&1; do sleep 2; done"

echo ""
echo "========================================="
echo "Staging refresh complete."
echo "========================================="
echo "Staging API: http://localhost:8001"
echo "Staging Web: http://localhost:5174"
echo ""
