# 09 — Compliance & Risk

## Data protection

### Kenya Data Protection Act (2019)

- MwalimuKit stores **personal data of minors** (learner names, school,
  assessment scores).
- We treat the school as the data controller and MwalimuKit as the data
  processor. v1.x will formalise a Data Processing Agreement in the
  school's onboarding flow.
- We collect the **minimum** data needed: name, optional admission
  number, optional gender. No biometric, no location, no photos in v0.1.

### Cross-border data transfers

- AI provider calls may send the sub-strand label and a free-text
  teacher prompt to OpenAI / Anthropic. We **never** send learner
  names, scores, or school identifiers to the AI provider.
- If a school requires zero outbound AI traffic, the "Manual" mode
  works fully offline.

### Children's data

- Learner records are scoped to a school; access is gated by the
  teacher's JWT.
- There is no public-facing page that lists learners.
- v1.x adds an "Export my data" + "Delete my school" flow to satisfy
  right-to-erasure requests.

## Security

- Passwords hashed with **argon2id**.
- All traffic TLS-only in production (HTTP→HTTPS redirect at the edge).
- JWT access tokens short-lived (15 min). Refresh tokens stored only
  in IndexedDB, never in cookies.
- Rate limiting on `/auth/login` and `/assessments/generate` via Redis.
- CSP locked down in the PWA's `index.html`.
- Dependency scanning via Dependabot (or equivalent) on the repo.

## Curriculum accuracy

- The KICD designs the curriculum. MwalimuKit **does not** alter the
  official strand/sub-strand labels or codes.
- v0.1 ships a seedable JSON catalogue; v0.2 will allow an admin to
  upload an updated KICD export without code changes.
- AI-generated items are clearly labelled "AI draft" until the teacher
  saves them; the teacher is the final author.

## Accessibility

- Target: WCAG 2.1 AA on the web app.
- Keyboard-navigable everywhere (tab order, focus rings, skip links).
- Colour contrast >= 4.5:1 for body text.
- All custom controls have ARIA roles and labels.
- Score grid supports arrow-key navigation between cells.

## Risk register

| Risk                                                          | Likelihood | Impact | Mitigation                                                        |
| ------------------------------------------------------------- | ---------- | ------ | ----------------------------------------------------------------- |
| KICD updates strand codes mid-term                             | Medium     | Medium | Versioned curriculum content; code reads strand code, not name.    |
| AI provider returns biased or off-CBC content                  | Medium     | Medium | Strict system prompt; teacher always reviews; "AI draft" badge.    |
| Schools with no internet at all                                | High       | High   | Full offline PWA + background sync; structured-template mode.      |
| Pilot school abandons the tool                                 | Medium     | Medium | Make export trivial; no lock-in; "Export my data" always works.   |
| Government mandates a different reporting format               | Low        | High   | Data model already separates `Score` from any report template.     |
| AI provider pricing spike                                      | Medium     | Medium | Pluggable provider; cached drafts; per-school monthly AI budget.   |
| Breach exposes learner data                                    | Low        | High   | Encryption at rest + TLS; per-school isolation; access logs v1.x.  |
| Adoption stalls below critical mass                            | Medium     | High   | Teacher-led GTM via WhatsApp groups; free during pilot.            |

## Ethical commitments

- We **will not** show learners' names to anyone outside their school.
- We **will not** sell or share learner data.
- We **will** publish a clear privacy policy before any school goes
  beyond a private demo.
- We **will** ship an "AI transparency" page that explains what the
  AI sees, when, and why.
