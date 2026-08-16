# 01 — Product Vision

## The problem

Kenya's Competency-Based Curriculum (CBC/CBE) shifted assessment away from
pure content recall and toward seven **core competencies** and continuous
formative assessment against rubrics. Teachers — especially in primary and
junior secondary — are now expected to:

- Plan lessons aligned to specific KICD strands and sub-strands
- Design or adapt rubric-based formative assessments per learning area
- Track every learner against multiple performance levels
- Compile report books that satisfy KPSEA / KJSEA expectations

In practice most teachers juggle this on paper notebooks, Word documents,
and ad-hoc Excel sheets. There is no mainstream, curriculum-aware tool
purpose-built for Kenyan teachers, and existing generic LMS platforms
ignore CBC's structure entirely.

## The product

**MwalimuKit** is an offline-first web app for Kenyan teachers that:

1. Generates rubric-aligned formative assessments from KICD strands and
   sub-strands in under a minute.
2. Lets teachers capture scores against the rubric on a phone or laptop,
   online **or offline**.
3. Will, in a later release, auto-compile CBC report books ready for
   KPSEA / KJSEA submission.

It is built for the day-to-day reality of a Kenyan classroom teacher —
low-bandwidth, mixed devices, intermittent connectivity — not for a
centralised ministry dashboard.

## Why now

- CBC has been fully rolled out through Grade 9; the first KPSEA cohort
  is in the system and teachers feel the reporting pressure.
- AI-grade generative models make "strand in, assessment + rubric out"
  feasible for the first time at the cost and latency a teacher can
  tolerate.
- Most existing tools (Google Forms, generic LMS) either don't speak CBC
  or require paid seats the schools can't afford.

## Differentiators

| Differentiator                        | Why it matters                                                |
| ------------------------------------- | ------------------------------------------------------------- |
| KICD-mapped learning areas & strands  | Teachers don't have to remember curriculum codes              |
| CBC-aware rubric scoring (4 levels)   | Matches the language and structure of the report book         |
| Offline-first PWA                     | Works in schools with flaky connectivity, installs like an app |
| Structured templates + AI generation  | Teachers who distrust AI have a fully manual fallback         |
| School-scoped multi-tenancy           | Each school's data is isolated; fits KEMIS/EMIS mental model   |
| Paywall-ready                         | Free during pilot; can monetise per-school or per-teacher      |

## Non-goals (v0.1)

- Replacing the Ministry's EMIS/KEMIS reporting systems
- A full LMS (no video, no chat, no attendance-by-camera)
- Parent-facing portals
- Curriculum design authority (KICD remains the source of truth)

## Success metrics (12-month horizon)

| Metric                                       | Target         |
| -------------------------------------------- | -------------- |
| Active teacher accounts                       | 1,000+         |
| Assessments generated                        | 25,000+        |
| Schools onboarded (at least one teacher)      | 200+           |
| Median time from strand-pick to saved item set | < 2 min        |
| Offline-score-entry usage share               | >= 40% of scores |

## North-star vision

Every Kenyan teacher, regardless of connectivity, can produce a
CBC-aligned formative assessment for any strand in any learning area in
under two minutes — and have all of it persist on the device, sync
when online, and roll up into a report book the school can hand to
KPSEA/JKSEA without rework.
