#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding curriculum data..."
python -m app.scripts.seed_curriculum

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
