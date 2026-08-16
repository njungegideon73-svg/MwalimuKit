# MwalimuKit

> **Plan. Assess. Report. Aligned to CBC, in minutes.**

MwalimuKit is an offline-first PWA that helps Kenyan teachers generate
rubric-aligned formative assessments from KICD strands/sub-strands, enter
scores offline, and (eventually) auto-generate KPSEA-ready report books.

This repository is a **monorepo** containing:

| Path                 | Purpose                                                       |
| -------------------- | ------------------------------------------------------------- |
| `web/`               | React + Vite teacher PWA (offline-first, installable)         |
| `api/`               | FastAPI backend (PostgreSQL + Redis + Alembic)                |
| `mobile/`            | Placeholder for the optional Android wrapper (Capacitor)      |
| `packages/shared/`   | Curriculum content, rubric JSON, and shared TS/Python types   |
| `infra/`             | `docker-compose.yml` for local dev                            |
| `docs/`              | Product, design, and engineering documentation                |
| `scripts/`           | Dev and seed scripts                                          |

---

## Quick start (local)

```bash
# 1. Boot the database, cache, API, and web app
docker compose -f infra/docker-compose.yml up --build

# 2. Run database migrations
docker compose -f infra/docker-compose.yml exec api alembic upgrade head

# 3. Seed the curriculum content (KICD strands/sub-strands)
docker compose -f infra/docker-compose.yml exec api python -m app.scripts.seed_curriculum
```

- Web: <http://localhost:5173>
- API: <http://localhost:8000/docs>

---

## MVP scope (v0.1)

1. **Rubric-based formative assessment generator**
   - Teacher picks learning area → strand → sub-strand
   - AI drafts 5 assessment items + scoring rubric (or structured template)
   - Teacher edits, saves, and reuses the assessment
2. **Class register + offline score entry**
   - Add learners to a class
   - Enter scores against the rubric
   - Background sync when the device comes back online
3. **Multi-tenancy**
   - School is the tenant; teachers are scoped to one school
   - Paywall-ready feature flags (free tier toggles on later)

Out of scope for v0.1: report book export, lesson plan generator, KJSEA/KPSEA
analytics dashboards, admin console. These land in v1.x.

---

## Tech stack

| Layer    | Choice                                                                  |
| -------- | ----------------------------------------------------------------------- |
| Frontend | React 18, Vite, TanStack Query, Zustand, Tailwind, shadcn/ui, Dexie     |
| Backend  | FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16, Redis 7                |
| Auth     | JWT (access + refresh) + school-scoped RBAC                              |
| AI       | Pluggable provider via `app/ai/provider.py` (OpenAI / Anthropic / mock) |
| Offline  | Service Worker + IndexedDB (Dexie) + Background Sync API                |
| Infra    | Docker Compose (dev) -> Fly.io + Supabase/Neon + Upstash (prod)          |

---

## Repository layout

```
mwalimukit/
|-- README.md
|-- docs/                       # 01-09 product & engineering docs
|-- infra/docker-compose.yml
|-- api/                        # FastAPI service
|-- web/                        # React + Vite PWA
|-- mobile/                     # Capacitor Android wrapper (later)
|-- packages/shared/            # Curriculum JSON, rubric templates, TS types
|-- scripts/                    # One-off scripts (seed, data import, etc.)
```

See `docs/06-architecture.md` for the full system diagram.
