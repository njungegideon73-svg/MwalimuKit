# 04 — Functional Specification (v0.1 MVP)

This is the contract between product, design, and engineering. Anything
not listed here is **not** in v0.1.

## 1. Authentication

### 1.1 Sign up

- Fields: full name, email, password (min 8 chars), school code.
- The school code is required in v0.1 — a seed script provisions one
  "Demo Primary School" with a known code for development.
- On success: account created in school `X`, JWT issued, user lands on
  the dashboard.

### 1.2 Log in

- Fields: email + password.
- Returns short-lived access token (15 min) + long-lived refresh token
  (30 days, stored in IndexedDB).

### 1.3 Roles (v0.1)

- `teacher` — full access to assessment + scoring within their school.
- `school_admin` — exists in the schema but no admin UI in v0.1.
- `super_admin` — exists in the schema; not exposed via UI in v0.1.

## 2. Curriculum browsing

- Curriculum data is loaded once at app start and cached in IndexedDB.
- UI: three cascading dropdowns — **Level → Learning Area → Strand** —
  with a free-text search box that filters strands by keyword.
- Each strand shows its official code (e.g. `NU-2.1.1`) and the KICD
  sub-strand list. Sub-strands are the leaves the assessment generator
  consumes.

## 3. Assessment generation

### 3.1 Two modes

1. **AI draft** (default if `FEATURE_AI_GENERATION_ENABLED=true`)
   - Teacher picks Level → Learning Area → Strand → Sub-strand.
   - System calls `POST /api/v1/assessments/generate` with the sub-strand
     code and the teacher's optional prompt.
   - Backend returns a draft: 5 items + a 4-level rubric.
   - Each item has: stem, optional `answer_guide`, and the rubric row it
     is scored against.
   - Teacher can edit any field, delete an item, or add a new item
     manually.
2. **Structured template**
   - Same strand-pick flow, but the AI call is skipped.
   - The UI renders a blank 5-row item table + a 4-level rubric editor.
   - Teacher fills cells manually.

### 3.2 Save

- The assessment is saved with: name, description, school, owner,
  learning area, strand, sub-strand(s), items[], rubric{}, tags[].
- Saved assessments appear in "My assessments" list with strand badges.

### 3.3 Library actions

- View, edit, duplicate, delete.
- Mark/unmark "favourite" for quick filter. (v0.1)

## 4. Class register & score entry

### 4.1 Classes

- Fields: name, grade level (PP1–Grade 9), learning area(s).
- A teacher can have multiple classes; a class belongs to exactly one
  teacher in v0.1.

### 4.2 Learners

- Fields: full name, optional admission number, optional gender.
- Bulk add: paste a CSV (one name per line, or `name,admission_no`).
- Edit / delete any learner; deleting a learner does **not** delete
  their historical scores (soft delete via `deleted_at`).

### 4.3 Score entry

- Open an assessment against a class → grid renders:
  - Rows = learners in the class.
  - Columns = rubric levels (1–4) per item (or per rubric criterion —
    see rubric model).
- Tap a cell to record a level. Tapping again clears it.
- Save is implicit; every change writes to IndexedDB first, then queues
  a sync to the server.
- Conflict policy: last-write-wins per cell, with a per-cell `updated_at`
  to detect divergence. v0.1 shows a "synced" / "pending" badge; v1.x
  surfaces real conflict UI.

### 4.4 Sync

- The PWA uses the Background Sync API where available, falling back to
  a retry-on-online-event listener.
- The sync worker batches score writes into a single
  `POST /api/v1/scores/batch` request.

## 5. Settings & data

- "Export my data" — JSON download of all assessments, classes,
  learners, and scores for the current user. Always free.
- "Sign out" — clears all local IndexedDB data after server-side
  revocation.

## 6. Paywall-ready toggle

- The server emits a `FeatureFlag` payload per request
  (`paywall_enabled`, `ai_generation_enabled`, `max_classes`,
  `max_learners_per_class`).
- v0.1 ships with `paywall_enabled=false` and `ai_generation_enabled=true`.
- The UI reads the flags and either hides, disables, or upgrades
  features accordingly. This is intentionally cheap to extend later.

## 7. Observability

- Backend: structured JSON logs to stdout.
- Frontend: Sentry-style error boundary (optional; behind env flag).
- AI calls are logged with token usage for cost tracking.

## 8. Out of scope (v0.1)

- Report book PDF export
- Lesson plan / scheme-of-work generator
- Admin dashboard (school or county level)
- Parent or learner portals
- SMS / USSD fallback
- Payments / subscription billing
