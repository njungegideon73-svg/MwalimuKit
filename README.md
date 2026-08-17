# MwalimuKit

![MwalimuKit banner](assets/mwalimukit-banner.svg)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Node](https://img.shields.io/badge/Node-%3E%3D20-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev/)

> Plan. Assess. Report. Aligned to CBC, in minutes.

MwalimuKit is an offline-first assessment platform for Kenyan schools. Teachers can generate rubric-aligned formative assessments from KICD strands and sub-strands, record learner scores offline, and prepare school-ready reporting workflows without dependence on constant connectivity.

This repository is a monorepo containing:

| Path               | Purpose                                           |
| ------------------ | ------------------------------------------------- |
| `web/`             | React + Vite teacher PWA                          |
| `api/`             | FastAPI backend with PostgreSQL and Redis         |
| `mobile/`          | Optional Android wrapper for future expansion     |
| `packages/shared/` | Curriculum content, rubric data, and shared types |
| `infra/`           | Docker setup and environment configuration        |
| `docs/`            | Product, design, and engineering documentation    |
| `scripts/`         | Utility scripts such as curriculum seeding        |

---

## Why this project exists

MwalimuKit helps teachers to:

- create learner-friendly, rubric-based assessments from CBC strands
- record scores even when the internet is unavailable
- organize marks around classes, learners, and schools
- prepare for reporting and analytics workflows without rebuilding the stack

---

## Requirements

Before running the project locally or deploying it, install:

- Node.js 20+
- npm 10+
- Python 3.11+
- Docker + Docker Compose
- Git

---

## Local setup

### 1) Clone the repository

```bash
git clone https://github.com/njungegideon73-svg/MwalimuKit.git
cd MwalimuKit
```

### 2) Install dependencies

```bash
npm install
```

### 3) Configure environment variables

Create local environment files before starting services.

```bash
cp .env.example .env
```

For the backend, set values like:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/mwalimukit
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change-me
OPENAI_API_KEY=your-key
CORS_ORIGINS=http://localhost:5173
```

For the frontend, set the API base URL:

```env
VITE_API_URL=http://localhost:8000
```

### 4) Start the local stack

```bash
docker compose -f infra/docker-compose.yml up --build
```

This boots the local stack for:

- PostgreSQL
- Redis
- the FastAPI backend
- the frontend app

### 5) Run database migrations

```bash
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
```

### 6) Seed curriculum data

```bash
docker compose -f infra/docker-compose.yml exec api python -m app.scripts.seed_curriculum
```

### 7) Open the app

- Web app: http://localhost:5173
- API docs: http://localhost:8000/docs

---

## Deployment guide

### Recommended deployment model

Use a small production setup with:

- frontend hosted on a static hosting provider or container platform
- backend deployed as a FastAPI service
- PostgreSQL and Redis managed separately
- environment variables injected securely via platform secret management

### Backend deployment checklist

1. Build the Python service in a production-ready environment.
2. Set the production database URL, Redis URL, and JWT secret.
3. Configure CORS for the deployed frontend domain.
4. Run migrations before starting the API workers.
5. Set up health checks and log collection.

Example:

```bash
cd api
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend deployment checklist

1. Set `VITE_API_URL` to the deployed backend URL.
2. Run the production build.
3. Serve the generated static output through a CDN or web host.

Example:

```bash
npm run build
```

### Docker deployment

For staging or a self-hosted environment, build and run the provided stack:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

Use a dedicated `.env` file or your CI/CD secret manager for production credentials.

---

## Development commands

From the repo root:

```bash
# Start the web app
npm run dev

# Build the frontend
npm run build

# Lint the frontend
npm run lint

# Type-check the frontend
npm run typecheck
```

For the Python service:

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

---

## MVP scope (v0.1)

1. Rubric-based formative assessment generation
2. Class register and offline score entry
3. Multi-tenancy with school-scoped access

Out of scope for v0.1: report book export, advanced analytics dashboards, and a full admin console.

---

## Tech stack

| Layer    | Choice                                                              |
| -------- | ------------------------------------------------------------------- |
| Frontend | React 18, Vite, TanStack Query, Zustand, Tailwind, shadcn/ui, Dexie |
| Backend  | FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16, Redis 7            |
| Auth     | JWT with school-scoped RBAC                                         |
| AI       | Pluggable provider via `api/app/ai/provider.py`                     |
| Offline  | Service worker + IndexedDB + background sync                        |
| Infra    | Docker Compose for local and containerized deployment               |

---

## Repository layout

```text
mwalimukit/
├── README.md
├── LICENSE
├── assets/
│   ├── mwalimukit-logo.svg
│   └── mwalimukit-banner.svg
├── docs/                       # product and engineering docs
├── infra/                      # containerized local setup
├── api/                        # FastAPI backend
├── web/                        # React + Vite frontend
├── mobile/                     # Android wrapper placeholder
├── packages/shared/            # curriculum and shared types
├── scripts/                    # utility scripts
├── package.json                # root workspace config
├── .gitignore                  # repo ignore rules
└── .env.example                # environment template
```

See the documentation in `docs/` for deeper design and architecture details.
