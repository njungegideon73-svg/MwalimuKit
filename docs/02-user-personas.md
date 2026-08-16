# 02 — User Personas

We optimise for the teacher first. Other personas are listed so we don't
break their flows when they show up later, but they are not the
design target of v0.1.

---

## P1 — Grace, the lower-primary classroom teacher (primary persona)

- **Demographics**
  - 28–40 years old, Diploma or Bachelor's in Education
  - Teaches Grade 1–3 in a public or low-cost private school
  - Has 30–45 learners in a single class
  - Device: a 4–5 year old Android phone + a shared laptop at school
- **Goals**
  - Cover the syllabus without falling behind
  - Generate quick formative checks that map to the strands she teaches
  - Track each learner's progress against the seven core competencies
  - Survive the term without drowning in paperwork
- **Frustrations**
  - Loses notes when her phone resets or when power goes
  - Spends weekends typing rubrics into Word from KICD PDFs
  - Doesn't know if her assessments actually test the right sub-strand
  - Internet at school is patchy; she can't rely on cloud-only tools
- **"Aha" moment for MwalimuKit**
  - Picks "Numeracy → Numbers → Counting 0–20" → gets a 5-item check
    with a 4-level rubric in < 30 seconds, edits one item, saves, and
    uses it the same day.

---

## P2 — Joseph, the Grade 7–9 junior secondary teacher

- **Demographics**
  - 30–50 years old, B.Ed or PGDE
  - Specialises in one or two learning areas (e.g. English, Kiswahili,
    Mathematics, Integrated Science)
  - Often teaches across two or three classes
- **Goals**
  - Prepare learners for KJSEA without teaching to a generic test
  - Keep assessment records per strand across the term
  - Use AI to draft assessment ideas he can adapt (he doesn't fully trust
    AI but it saves time)
- **Frustrations**
  - Generic AI tools give him North-American context examples
  - He wants assessment items that use Kenyan names, currencies, places
  - Rubrics from KICD PDFs are long; he wants short, actionable ones
- **"Aha" moment for MwalimuKit**
  - Switches between "AI draft" and "structured template" modes for the
    same strand; templates when he wants full control, AI when he needs
    speed.

---

## P3 — Mary, the school headteacher / deputy (secondary persona)

- **Demographics**
  - 35–55, school administrator
  - Owns the laptops in the staffroom, approves tool purchases
  - Doesn't enter scores herself, but signs off on report books
- **Goals**
  - Confirm her teachers are assessing against the right strands
  - Get a clean PDF report book at end of term
  - Keep the school's data private (it's her legal responsibility)
- **Frustrations**
  - Has no overview of what's been assessed across the school
  - Suspects teachers are using WhatsApp to send her assessment photos
- **"Aha" moment for MwalimuKit** (v1.x)
  - Sees a school-wide dashboard of completed assessments per class per
    strand, and downloads a consolidated report book PDF.

---

## P4 — Daniel, the county curriculum support officer (tertiary persona)

- **Demographics**
  - KICD / county MoE staff
  - Aggregates data across many schools for KJSEA / KPSEA readiness
- **Why we list him**
  - We **do not** build for him in v0.1. We ensure our data model could
    be rolled up to county level without schema rewrites when the time
    comes (school → county via `school.county_id`).
