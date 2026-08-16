# Local infrastructure

This directory contains the Docker Compose stack used for local development.

## Services

| Service | Port | Notes                                              |
| ------- | ---- | -------------------------------------------------- |
| `db`    | 5432 | PostgreSQL 16 (volume-backed)                      |
| `redis` | 6379 | Redis 7 for rate limiting + background jobs        |
| `api`   | 8000 | FastAPI service (auto-runs migrations + seed)      |
| `web`   | 5173 | Vite dev server for the teacher PWA                |

## Bring it up

```bash
cp .env.example .env       # edit secrets if you want real AI keys
docker compose -f infra/docker-compose.yml up --build
```

## Reset the database

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build
```
