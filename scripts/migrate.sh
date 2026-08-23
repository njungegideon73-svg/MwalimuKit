#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MwalimuKit — Safe Migration Runner (Expand/Contract Pattern)
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./scripts/migrate.sh status                              # list all migrations
#   ./scripts/migrate.sh apply <migration_id>                # run up to switch (pauses)
#   ./scripts/migrate.sh apply <migration_id> --no-confirm   # run ALL phases
#   ./scripts/migrate.sh rollback <migration_id>             # undo a migration
#   ./scripts/migrate.sh verify <migration_id>               # verify a completed migration
#   ./scripts/migrate.sh plan <migration_id>                 # show rollback plan
# ─────────────────────────────────────────────────────────────
set -euo pipefail

ACTION="${1:-status}"
MIGRATION_ID="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env.staging" ]; then
    ENV_FILE="$PROJECT_ROOT/.env.staging"
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.staging.yml"
elif [ -f "$PROJECT_ROOT/.env.production" ]; then
    ENV_FILE="$PROJECT_ROOT/.env.production"
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.prod.yml"
else
    echo "[migrate] ERROR: No .env.staging or .env.production found" >&2
    exit 1
fi

COMPOSE_OPTS="-f $COMPOSE_FILE --env-file $ENV_FILE"

run_migrate() {
    docker compose $COMPOSE_OPTS exec -T api python -m migrations.cli "$@"
}

case "$ACTION" in
    status|apply|rollback|verify|plan)
        run_migrate "$ACTION" "$MIGRATION_ID" "${3:-}"
        ;;
    *)
        echo "Usage: $0 {status|apply|rollback|verify|plan} [migration_id] [--no-confirm]"
        exit 1
        ;;
esac
