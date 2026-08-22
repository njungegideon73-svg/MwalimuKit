# 06 — Architecture

## High-level diagram

```
+----------------------+         +------------------------+
|  Browser / PWA       |  HTTPS  |  FastAPI backend       |
|                      | <-----> |  (api/app)             |
|  - React + Vite      |         |                        |
|  - Dexie (IndexedDB) |         |  - Routers             |
|  - Service Worker    |         |  - Services            |
|  - Background Sync   |         |  - AI provider (proxy) |
+----------+-----------+         +-----------+------------+
           |                                 |
           |   (background sync)             |
           v                                 v
   Local IndexedDB                   +-------+--------+
   - curriculum (read)               | PostgreSQL 16  |
   - user data (read/write)          +----------------+
   - sync queue                      +-------+--------+
                                             |
                                             v
                                    +--------+--------+
                                    | Redis 7         |
                                    | (rate limit,     |
                                    |  job queue)     |
                                    +-----------------+

   +------------------------+
   | External AI provider   |  <-- only the API talks to this
   | (OpenAI / Anthropic)   |
   +------------------------+
```

## Components

### Web app (`web/`)

- **React 18 + Vite + TypeScript** for fast dev cycles.
- **Route-level code splitting**: every page is loaded via
  `React.lazy()` (`web/src/app/App.tsx`) so the initial bundle stays
  small on low-bandwidth connections; a shared spinner shows while a
  chunk loads.
- **TanStack Query** for server state, with a custom "persisted
  query client" that uses Dexie as the backing store so data survives
  reloads.
- **Zustand** for small slices of UI state.
- **Dexie** for IndexedDB (schema v2, numeric `_dirty: 0 | 1` sync flag —
  see `docs/05-data-model.md`).
- **shadcn/ui + Tailwind** for components.
- **Workbox** for the service worker (precaching + runtime caching, see
  "Offline strategy").
- **react-hook-form + zod** for forms and validation.

### Backend (`api/`)

- **FastAPI** with explicit routers per domain
  (`auth`, `schools`, `curriculum`, `assessments`, `history`, `classes`,
  `learners`, `runs`, `scores`, `reports`, `news`, `term_exams`,
  `billing`, `admin`, `feature_flags`, `super_admin`, `school_admin`).
  Shared admin business logic lives in `app/services/admin.py`.
- **SQLAlchemy 2.x** with async sessions (`asyncpg`).
- **Alembic** for migrations (`0001`–`0007`).
- **Redis** for rate limits and (later) background jobs.
- **Pydantic v2** for schemas.
- **Argon2** for password hashing.
- **python-jose** for JWT.

### Cross-cutting concerns

- **Rate limiting** (IP-based, Redis-backed, degrades gracefully):
  login 5/min, signup 5/min, refresh 30/min, AI generate 10/min.
- **Password policy**: minimum 8 characters with at least one letter and
  one digit, enforced by a Pydantic validator on signup, password change,
  and admin-created users.
- **CSRF posture**: the API uses bearer tokens (never auto-attached by
  browsers), and CORS origins are explicit — never a wildcard paired
  with credentials. OPTIONS preflight requests for state-changing
  endpoints are covered by tests in `api/tests/test_cors_preflight.py`,
  run in CI (`.github/workflows/ci.yml`).
- **Health checks**: `GET /health` is a liveness probe;
  `GET /ready` verifies DB connectivity (and reports Redis status) and
  returns 503 when the database is unreachable. Both containers define
  healthchecks in `docker-compose.yml` / their Dockerfiles.

### Shared package (`packages/shared/`)

- TypeScript types that mirror the API contract.
- A JSON catalogue of CBC learning areas, strands, and sub-strands
  (seeded into the DB and bundled into the web app for offline use).
- Default rubric JSON used when AI generation is disabled.

### Mobile (`mobile/`)

- v0.1: the PWA is installable on Android via "Add to Home Screen".
  No native code yet.
- v1.x (optional): wrap the same web build with **Capacitor** and ship
  an APK / AAB. The PWA stays the source of truth.

## Offline strategy

1. On first load (online), the service worker precaches the app shell
   and the curriculum JSON.
2. On login, the app fetches the user's assessments, classes, learners,
   and any in-progress runs, and writes them into Dexie.
3. All writes go to Dexie first. Each row is marked `_dirty = 1` and
   queued by entity type.
4. The Background Sync API (or a `online` event fallback) drains the
   queue. Batch endpoints accept a list of writes with client-side
   UUIDs for idempotency.
5. API responses are cached per data class (`web/vite.config.ts`):

   | Policy | Endpoints | Rationale |
   | ------ | --------- | --------- |
   | Cache-first (7 days) | `GET /curriculum/catalogue` | static reference data |
   | Network-only | `/assessments/*`, `/scores/*`, `/runs/*`, `/auth/*` | live data + mutations must never be stale on shared devices |
   | Network-first (5 min TTL) | `/classes/*`, `/learners/*` | offline fallback that ages out quickly |

   Workbox runtime routes only intercept GETs; POST/PATCH/DELETE always
   hit the network.

## Authentication flow

- Email + password → `POST /auth/login` → `{ access, refresh }`.
- Access token (15 min) sent on every API call as `Authorization:
  Bearer ...`.
- Refresh token (30 days) stored in IndexedDB; if a 401 hits, the web
  app tries to refresh once before showing "Session expired".
- All data endpoints scope by `school_id` derived from the JWT — the
  client never sends `school_id`.

## AI provider abstraction

`api/app/ai/provider.py` defines an interface:

```python
class AIProvider(Protocol):
    async def generate_assessment(
        self,
        *,
        learning_area: str,
        strand: str,
        sub_strand: str,
        grade_level: str,
        teacher_prompt: str | None = None,
    ) -> GeneratedAssessment: ...
```

Two implementations ship:

- `MockProvider` — returns deterministic stub data so the app is usable
  end-to-end without an API key.
- `OpenAIProvider` (and an AnthropicProvider) — real calls. The choice
  is env-driven (`AI_PROVIDER`).

The system prompt constrains the model to:

- Kenyan context (names, places, currency in KES, English/Kiswahili
  aware).
- 4-level CBC rubric vocabulary.
- 5 items by default, configurable.

## Deployment

- **Dev**: `docker compose` from `infra/`.
- **Prod**: managed hosting
  - Web: Fly.io (or Render static site).
  - API: Fly.io / Render.
  - DB: Supabase Postgres or Neon.
  - Redis: Upstash.
  - Object storage (later, for PDFs): Cloudflare R2.

The repository contains a single `Dockerfile` per service and a
`fly.toml` stub in `infra/fly.toml.example`.
