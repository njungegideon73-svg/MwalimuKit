#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MwalimuKit — Rollback a migration immediately
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./scripts/migrate-rollback.sh 0012_example_rename
#
# This undoes ALL phases of the specified migration, returning
# the database to its pre-migration state.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <migration_id>" >&2
    exit 1
fi

MIGRATION_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env.staging" ]; then
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.staging.yml"
    ENV_FILE="$PROJECT_ROOT/.env.staging"
elif [ -f "$PROJECT_ROOT/.env.production" ]; then
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.prod.yml"
    ENV_FILE="$PROJECT_ROOT/.env.production"
else
    echo "[rollback] ERROR: No .env.staging or .env.production found" >&2
    exit 1
fi

COMPOSE_OPTS="-f $COMPOSE_FILE --env-file $ENV_FILE"

echo "========================================="
echo "MwalimuKit Migration Rollback"
echo "========================================="
echo ""
echo "Migration:  $MIGRATION_ID"
echo "Environment: $([ -f "$PROJECT_ROOT/.env.staging" ] && echo staging || echo production)"
echo ""
echo "This will undo ALL phases of the migration."
echo "The database will return to its pre-migration state."
echo ""
read -p "Are you sure? (type 'YES' to confirm): " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "Rollback cancelled."
    exit 0
fi

echo "[rollback] Taking pre-rollback snapshot..."
$PROJECT_ROOT/scripts/backup.sh

echo "[rollback] Rolling back migration..."
docker compose $COMPOSE_OPTS exec -T api python -c "
import asyncio
from migrations.runner import MigrationRunner
from app.core.db import engine

async def main():
    async with engine.begin() as conn:
        runner = MigrationRunner(conn)
        await runner.ensure_migrations_table()
        await runner.rollback('$MIGRATION_ID')

asyncio.run(main())
"

echo "[rollback] Verifying rollback..."
docker compose $COMPOSE_OPTS exec -T api python -c "
import asyncio
from migrations.runner import MigrationRunner
from app.core.db import engine

async def main():
    async with engine.begin() as conn:
        runner = MigrationRunner(conn)
        await runner.ensure_migrations_table()
        record = await runner.get_record('$MIGRATION_ID')
        if record and record.status == 'rolled_back':
            print('[rollback] SUCCESS: Migration rolled back.')
        else:
            print('[rollback] WARNING: Migration status is ' + str(record.status if record else 'unknown'))

asyncio.run(main())
"

echo "[rollback] Running health check..."
docker compose $COMPOSE_OPTS exec -T api curl -sf http://localhost:8000/health || {
    echo "[rollback] ERROR: Health check failed after rollback" >&2
    exit 1
}

echo ""
echo "========================================="
echo "Rollback complete."
echo "========================================="
