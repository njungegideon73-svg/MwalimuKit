#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MwalimuKit — Check migration status
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env.staging" ]; then
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.staging.yml"
    ENV_FILE="$PROJECT_ROOT/.env.staging"
elif [ -f "$PROJECT_ROOT/.env.production" ]; then
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.prod.yml"
    ENV_FILE="$PROJECT_ROOT/.env.production"
else
    echo "[migrate-status] ERROR: No .env.staging or .env.production found" >&2
    exit 1
fi

COMPOSE_OPTS="-f $COMPOSE_FILE --env-file $ENV_FILE"

echo "Checking migration status..."
docker compose $COMPOSE_OPTS exec -T api python -c "
import asyncio
from migrations.runner import MigrationRunner
from app.core.db import engine
from migrations.rollback import print_rollback_plan, Phase

async def main():
    async with engine.begin() as conn:
        runner = MigrationRunner(conn)
        await runner.ensure_migrations_table()
        records = await runner.list_records()

        if not records:
            print('No migrations tracked yet.')
            return

        print(f'{\"ID\":<40} {\"Phase\":<12} {\"Status\":<12} {\"Started\":<20}')
        print('-' * 90)
        for r in records:
            started = r.started_at.strftime('%Y-%m-%d %H:%M') if r.started_at else '-'
            print(f'{r.id:<40} {r.phase:<12} {r.status:<12} {started:<20}')

        failed = [r for r in records if r.status == 'failed']
        if failed:
            print()
            print('FAILED MIGRATIONS:')
            for r in failed:
                print(f'  {r.id}: {r.name}')

asyncio.run(main())
"
