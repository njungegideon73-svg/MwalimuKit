# 07 — UX Flows

The flows below are written from the perspective of **Grace**, the
lower-primary teacher persona. They are the v0.1 happy paths. Edge
cases (offline, AI failure, etc.) are noted inline.

## F1 — First-run onboarding

```
+-----------------------------+
|  Landing page               |
|  "Sign up to start"         |
+-----------------------------+
              |
              v
+-----------------------------+
|  Sign-up form               |
|  - full name                |
|  - email                    |
|  - password                 |
|  - school code [hint link]  |
+-----------------------------+
              |
              v
+-----------------------------+
|  Dashboard (empty state)    |
|  "Pick a learning area to   |
|   generate your first       |
|   assessment"               |
+-----------------------------+
```

- Offline during sign-up? The form is **blocked** (we need the school
  to exist on the server). We show a clear message: "Sign-up needs
  internet the first time. After that, everything works offline."

## F2 — Generate an AI assessment

```
+-----------------------------+
|  Sidebar:                   |
|   Dashboard                 |
|   Assessments               |
|   Classes                   |
|   Settings                  |
+-----------------------------+
              |
              v
+-----------------------------+
|  Assessments page           |
|  [+ New assessment]         |
+-----------------------------+
              |
              v
+-----------------------------+
|  Step 1: Pick strand        |
|  [Level v] [Area v]         |
|  [Strand v] [Sub-strand v]  |
|  Mode: ( ) AI   ( ) Manual  |
|  [Generate draft]           |
+-----------------------------+
              |
   (loading indicator; offline-aware:
    if offline and AI selected,
    app auto-switches to Manual)
              |
              v
+-----------------------------+
|  Step 2: Edit assessment    |
|  Name: [_______________]    |
|  Items (5):                 |
|   1. stem [_______]         |
|       answer [_______]      |
|   2. ...                    |
|  Rubric (4 levels):         |
|   L1: Below expectation     |
|       [descriptor]          |
|   ...                       |
|  [Save] [Save & run later]  |
+-----------------------------+
              |
              v
+-----------------------------+
|  Saved assessment detail    |
|  [Run against a class]      |
+-----------------------------+
```

### Edge cases

- **AI timeout**: show "The AI is slow today — switch to manual?"
  with a one-click toggle that re-renders the manual editor.
- **AI returns < 5 items**: the editor still saves what's there;
  teacher can add the rest.
- **AI off / paywall on**: the "AI" radio is hidden, only "Manual"
  is shown.

## F3 — Score entry (offline-first)

```
+-----------------------------+
|  Class detail               |
|  Learners (list)            |
|  Assessments (list)         |
+-----------------------------+
              |
              v
+-----------------------------+
|  Pick assessment            |
|  -> "Counting 0-20 check"   |
+-----------------------------+
              |
              v
+-----------------------------+
|  Score grid                 |
|  +-----------+--+--+--+--+  |
|  | Learner   |L1|L2|L3|L4|  |
|  +-----------+--+--+--+--+  |
|  | Achieng   | .| X| .| .|  |
|  | Baraka    | .| .| X| .|  |
|  | ...       |                  |
|  +-----------+--+--+--+--+  |
|  Status: [Saved offline]    |
|  [Sync now]                 |
+-----------------------------+
```

- Tapping a cell writes to Dexie immediately.
- The "Saved offline" pill turns into a spinner when a sync attempt
  starts, then to "Synced" or "Retry" depending on result.
- Background Sync API handles automatic retries when the OS allows.
- Closing the tab never loses data — the Dexie row survives.

## F4 — Conflict resolution (v0.1)

- If the server has a newer `updated_at` for a cell, the **server
  wins**. The web app surfaces a non-blocking toast: "2 of your
  scores were updated by another device — here's what changed." The
  user can accept (default) or open a side-by-side diff.

## Visual design principles

- **Two-pane layout** on desktop (sidebar + main), **bottom-tab nav**
  on mobile (Home / Assessments / Classes / Settings).
- **Type scale** based on a 1.250 modular scale; minimum 16 px body.
- **Colour**: primary `#0E7C66` (deep green — friendly, Kenyan),
  accent `#F4A300` (warm amber for "saved" / success).
- **Iconography**: Lucide React icons, 1.5 px stroke.
- **Empty states always have one primary action** ("Generate your
  first assessment").
- **Loading**: skeletons, never spinners on first paint.
