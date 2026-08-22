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
if [ "$WORKERS" = "1" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
  echo "Starting $WORKERS Uvicorn workers via gunicorn..."
  exec gunicorn -k uvicorn.workers.UvicornWorker -w "$WORKERS" -b 0.0.0.0:8000 app.main:app
fi
