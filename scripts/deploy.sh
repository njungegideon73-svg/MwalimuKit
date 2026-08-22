#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# MwalimuKit — Production deployment script
# ─────────────────────────────────────────────────────────────
# Deploys the full production stack via docker-compose with zero-downtime
# rolling restart of the API workers behind nginx.
#
# Prerequisites:
#   - Docker + Docker Compose v2
#   - .env.production file with real secrets (see .env.example)
#
# Usage:
#   ./scripts/deploy.sh [staging|production] [apply]
#   ./scripts/deploy.sh production apply        # deploy + run migrations
#   ./scripts/deploy.sh production rollback     # rollback last deploy
# ─────────────────────────────────────────────────────────────
set -euo pipefail

ENV="${1:-production}"
ACTION="${2:-deploy}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ENV_FILE="$PROJECT_ROOT/.env.$ENV"
if [ ! -f "$ENV_FILE" ]; then
  echo "[deploy] ERROR: $ENV_FILE not found. Copy .env.example to .env.$ENV and fill in secrets." >&2
  exit 1
fi

COMPOSE_FILE="-f $PROJECT_ROOT/docker-compose.yml -f $PROJECT_ROOT/infra/docker-compose.prod.yml"

# ── Build images ─────────────────────────────────────────────
if [ "$ACTION" = "deploy" ] || [ "$ACTION" = "apply" ]; then
  echo "[deploy] Building images…"
  docker compose $COMPOSE_FILE build --parallel

  echo "[deploy] Deploying stack…"
  docker compose $COMPOSE_FILE --env-file "$ENV_FILE" up -d --no-deps --scale api=${API_WORKERS:-4} api web db redis nginx

  echo "[deploy] Waiting for API to be healthy…"
  timeout 60 docker compose $COMPOSE_FILE --env-file "$ENV_FILE" exec -T api \
    sh -c 'while ! curl -sf http://localhost:8000/health >/dev/null 2>&1; do sleep 2; done'

  echo "[deploy] Running database migrations…"
  docker compose $COMPOSE_FILE --env-file "$ENV_FILE" exec -T api alembic upgrade head

  echo "[deploy] Seeding curriculum (idempotent)…"
  docker compose $COMPOSE_FILE --env-file "$ENV_FILE" exec -T api \
    python -m app.scripts.seed_curriculum

  echo "[deploy] Reloading nginx to pick up new upstreams…"
  docker compose $COMPOSE_FILE --env-file "$ENV_FILE" exec -T nginx \
    nginx -s reload || true

  echo "[deploy] Verifying…"
  curl -fsS "https://${DOMAIN:-mwalimukit.co.ke}/health" || \
    curl -fsS "http://localhost:80/health"

  echo ""
  echo "[deploy] Deploy complete."
fi

# ── Rollback ─────────────────────────────────────────────────
if [ "$ACTION" = "rollback" ]; then
  echo "[deploy] Rolling back API containers…"
  docker compose $COMPOSE_FILE --env-file "$ENV_FILE" up -d --no-deps api
  echo "[deploy] Rollback complete."
fi

# ── Cleanup old images ──────────────────────────────────────
echo "[deploy] Pruning old images…"
docker image prune -f
echo "[deploy] Done."
