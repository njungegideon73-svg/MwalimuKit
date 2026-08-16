# 08 — Roadmap

## v0.1 — MVP (current target)

Goal: a teacher can sign up, pick a strand, get an assessment + rubric,
save it, enter scores against a class, and sync — online and offline.

Scope:

- Curriculum data: seed Lower Primary + a Grade 7 band (representative
  slice across learning areas). Architecture supports adding the rest as
  data.
- AI assessment generation + structured templates.
- Class register + offline score entry + background sync.
- School-scoped multi-tenancy.
- Paywall-ready feature flags.
- Docker Compose local dev.

Definition of done:

- A fresh developer can `docker compose up` and reach the app.
- A teacher can complete the F1→F2→F3 flows above without manual fixes.
- All Lighthouse PWA checks pass (installable, offline shell).
- Test coverage on the backend: >= 70% on services, >= 50% overall.
- Test coverage on the web: smoke tests for the three flows.

## v0.2 — Polish & content

- Full curriculum content for all primary levels + JSS (data only;
  no code changes needed).
- Better rubric editing UX (drag to reorder criteria, level colour
  picker).
- AI prompt history and "improve with feedback" iteration.
- Settings: change school code, change password.
- Beta with 3 pilot schools.

## v1.0 — Reports & admin

- Per-learner report card PDF (KPSEA-friendly).
- Class summary CSV.
- School admin dashboard (counts only).
- Stripe-backed subscription billing (per-school).
- Public roadmap page for teachers to vote on features.

## v1.x — County & parent layers

- County rollup dashboards (read-only).
- Optional parent SMS digest ("Term 2 report for Achieng is ready").
- Capacitor wrapper for a Play Store Android app.
- USSD / SMS fallback for teachers without smartphones. (Speculative.)

## What we explicitly do **not** plan

- Replacing EMIS/KEMIS — we feed into them, not compete.
- A full LMS — we're assessment-first.
- Live tutoring or chat.
