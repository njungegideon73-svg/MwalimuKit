#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding curriculum data..."
python -m app.scripts.seed_curriculum

echo "Starting API server..."
# Use a single Uvicorn worker when API_WORKERS is unset (matches the
# original behaviour).  When API_WORKERS > 1, gunicorn orchestrates the
# workers for graceful restarts under Docker / ECS.
WORKERS="${API_WORKERS:-2}"
# Use PORT if set by the host (e.g. Render, Heroku), otherwise default to 8000
API_PORT="${PORT:-8000}"
if [ "$WORKERS" = "1" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT"
else
  echo "Starting $WORKERS Uvicorn workers via gunicorn on port $API_PORT..."
  exec gunicorn -k uvicorn.workers.UvicornWorker -w "$WORKERS" -b "0.0.0.0:$API_PORT" app.main:app
fi
