#!/usr/bin/env bash
# Restore a MwalimuKit database backup produced by scripts/backup.sh.
#
# Usage:
#   ./scripts/restore.sh backups/mwalimukit-20260822T000000Z.dump.gz
#
# WARNING: this replaces the current contents of the database. The app is
# stopped first and restarted afterwards.
set -euo pipefail

FILE="${1:?Usage: $0 <backup.dump.gz>}"
COMPOSE="${COMPOSE:-docker compose}"

if [ ! -f "$FILE" ]; then
  echo "Backup file not found: $FILE" >&2
  exit 1
fi

echo "[restore] verifying $FILE"
gunzip -c "$FILE" | head -c 5 | grep -q "PGDMP" || { echo "Not a valid dump" >&2; exit 1; }

echo "[restore] stopping api + web"
$COMPOSE stop api web || true

echo "[restore] dropping and recreating database"
$COMPOSE exec -T db psql -U mwalimu -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='mwalimukit' AND pid <> pg_backend_pid();"
$COMPOSE exec -T db psql -U mwalimu -d postgres -c "DROP DATABASE IF EXISTS mwalimukit;"
$COMPOSE exec -T db psql -U mwalimu -d postgres -c "CREATE DATABASE mwalimukit OWNER mwalimu;"

echo "[restore] restoring"
gunzip -c "$FILE" | $COMPOSE exec -T db pg_restore -U mwalimu -d mwalimukit --no-owner --role=mwalimu

echo "[restore] starting services"
$COMPOSE up -d api web

echo "[restore] done — verify with: curl -f http://localhost:8000/ready"
