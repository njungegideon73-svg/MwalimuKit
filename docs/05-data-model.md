# 05 — Data Model

All entities are multi-tenant scoped by `school_id`. The model is
designed so a county-level aggregation layer can be added later without
schema rewrites.

> **Schema source of truth:** `api/alembic/versions/`. Migrations are
> numbered `0001`–`0007` (`0001` initial, `0002` assessment strand codes,
> `0003` missing tables, `0004` seed super admin, `0005` news items,
> `0006` SBA tables, `0007` activity logs). When a migration changes the
> schema, update this document in the same PR.

## ER overview (text)

```
School 1---* User
School 1---* Class          (a class is created by a teacher)
User   1---* Class
Class  1---* Learner
Class  1---* AssessmentRun (a "session" of an assessment against a class)
AssessmentRun 1---* Score
AssessmentRun *---1 Assessment (the reusable template)

User   1---* Assessment    (saved templates owned by a teacher)
Assessment  *---* SubStrand (an assessment targets one or more sub-strands)

LearningArea 1---* Strand 1---* SubStrand

TermExam 1---* LearnerExamScore  (SBA marks entry)

User 1---* ActivityLog           (audit trail)
FeatureRequest 1---* FeatureVote
```

## Tables (PostgreSQL)

All tables include `created_at`, `updated_at` (TIMESTAMPTZ). Soft-delete
via `deleted_at` only on user-generated content (Learner, Class,
Assessment).

### `schools`
| Column        | Type             | Notes                       |
| ------------- | ---------------- | --------------------------- |
| id            | uuid PK          |                             |
| name          | text NOT NULL    |                             |
| code          | text UNIQUE NOT NULL | 6-char join code         |
| county        | text NULL        | for v1.x aggregation        |
| level         | text NULL        | primary / jss / mixed       |
| settings      | jsonb NOT NULL DEFAULT '{}' | per-school overrides |

### `users`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| school_id     | uuid FK schools  |                                        |
| email         | citext UNIQUE NOT NULL | scoped to global uniqueness      |
| full_name     | text NOT NULL    |                                        |
| role          | enum('teacher','school_admin','super_admin') | default `teacher` |
| password_hash | text NOT NULL    |                                        |
| last_login_at | timestamptz NULL|                                        |
| is_active     | bool NOT NULL DEFAULT true |                              |

### `learning_areas`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| code          | text UNIQUE NOT NULL | e.g. `LP-MATH`                      |
| name          | text NOT NULL    |                                        |
| level         | enum('lower_primary','upper_primary','jss') |                       |
| sort_order    | int              |                                        |

### `strands`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| learning_area_id | uuid FK       |                                        |
| code          | text UNIQUE NOT NULL | e.g. `LP-MATH-NUM-2`               |
| name          | text NOT NULL    |                                        |
| sort_order    | int              |                                        |

### `sub_strands`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| strand_id     | uuid FK          |                                        |
| code          | text UNIQUE NOT NULL | e.g. `LP-MATH-NUM-2.1`             |
| name          | text NOT NULL    |                                        |
| sort_order    | int              |                                        |

### `assessments` (templates)
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| owner_id      | uuid FK users    |                                        |
| school_id     | uuid FK schools  | denormalised for tenant filtering       |
| name          | text NOT NULL    |                                        |
| description   | text NULL        |                                        |
| learning_area_id | uuid FK       |                                        |
| source        | enum('ai','manual','template') | how it was created     |
| rubric        | jsonb NOT NULL   | see rubric schema below                |
| items         | jsonb NOT NULL   | see item schema below                  |
| tags          | text[] NOT NULL DEFAULT '{}' |                                   |
| is_favourite  | bool NOT NULL DEFAULT false |                                   |
| deleted_at    | timestamptz NULL |                                        |

### `classes`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| school_id     | uuid FK schools  |                                        |
| teacher_id    | uuid FK users    |                                        |
| name          | text NOT NULL    |                                        |
| grade_level   | text NOT NULL    | free text in v0.1 (PP1..Grade 9)        |
| learning_area_ids | uuid[]      |                                        |
| deleted_at    | timestamptz NULL |                                        |

### `learners`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| school_id     | uuid FK schools  |                                        |
| class_id      | uuid FK classes  |                                        |
| full_name     | text NOT NULL    |                                        |
| admission_no  | text NULL        |                                        |
| gender        | text NULL        |                                        |
| deleted_at    | timestamptz NULL |                                        |

### `assessment_runs`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| school_id     | uuid FK          |                                        |
| class_id      | uuid FK          |                                        |
| assessment_id | uuid FK          |                                        |
| term          | text NULL        | e.g. `Term 2 2026`                      |
| started_at    | timestamptz NOT NULL DEFAULT now() |                          |
| closed_at     | timestamptz NULL |                                        |

### `scores`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          | client-generated UUID for offline idempotency |
| run_id        | uuid FK          |                                        |
| learner_id    | uuid FK          |                                        |
| item_id       | text NOT NULL    | matches `Assessment.items[].id`        |
| level         | smallint NULL    | 1..4, NULL = not yet scored            |
| note          | text NULL        |                                        |
| updated_at    | timestamptz NOT NULL | per-cell conflict resolution        |
| UNIQUE (run_id, learner_id, item_id) |     | idempotency on sync                  |

### `term_exams` (SBA)
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| school_id     | uuid FK schools  |                                        |
| class_id      | uuid FK classes  |                                        |
| learning_area_id | uuid FK learning_areas |                               |
| term          | int NOT NULL     | 1, 2 or 3                              |
| exam_type     | text NOT NULL    | opener / midterm / endterm             |
| academic_year | text NOT NULL    | e.g. `2025`                            |
| max_marks     | int NOT NULL DEFAULT 100 |                                |

### `learner_exam_scores` (SBA)
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| term_exam_id  | uuid FK term_exams |                                      |
| learner_id    | uuid FK learners |                                        |
| marks         | int NOT NULL     | 0..max_marks                           |
| grade         | text NULL        | optional letter grade                  |
| comment       | text NULL        | optional teacher comment               |

### `news_items`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| title         | text NOT NULL    |                                        |
| content       | text NOT NULL    |                                        |
| category      | text NOT NULL DEFAULT 'news' | news / update / announcement |
| is_active     | bool NOT NULL DEFAULT true |                             |
| created_by    | uuid FK users    |                                        |

### `feature_requests`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| title         | text NOT NULL    |                                        |
| description   | text NOT NULL    |                                        |
| status        | text NOT NULL DEFAULT 'open' | open / planned / done      |
| vote_count    | int NOT NULL DEFAULT 0 | denormalised for sorting         |

### `feature_votes`
| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| feature_id    | uuid FK feature_requests |                                |
| user_id       | uuid FK users    |                                        |
| UNIQUE (feature_id, user_id) | one vote per user per request           |

### `activity_logs`
Append-only audit trail written by `log_activity()`.

| Column        | Type             | Notes                                  |
| ------------- | ---------------- | -------------------------------------- |
| id            | uuid PK          |                                        |
| user_id       | uuid FK users NULL | actor (NULL for system events)       |
| school_id     | uuid FK schools NULL | tenant scope                       |
| action        | text NOT NULL    | dotted key, e.g. `auth.login`          |
| details       | jsonb NULL       | free-form context                      |

Queried via `GET /api/v1/admin/activity-log` (paginated; filter by
user/school/action/date) and `GET /api/v1/super-admin/activities`.

### `subscriptions`, `prompt_history`, `feature_flags`
Supporting tables: Stripe billing state per school, AI prompt/response
history per generation, and runtime feature-flag overrides keyed by
`key` with a JSONB `value`.

## JSON schemas

### `Assessment.rubric`

```json
{
  "levels": [
    { "level": 1, "label": "Below expectation",   "descriptor": "..." },
    { "level": 2, "label": "Approaching expectation", "descriptor": "..." },
    { "level": 3, "label": "Meeting expectation", "descriptor": "..." },
    { "level": 4, "label": "Exceeding expectation","descriptor": "..." }
  ],
  "criteria": [
    { "id": "accuracy",  "label": "Accuracy of response" },
    { "id": "reasoning", "label": "Reasoning / justification" }
  ]
}
```

> The 4-level vocabulary mirrors KICD's report book language.

### `Assessment.items`

```json
[
  {
    "id": "itm_01",
    "criterion": "accuracy",
    "stem": "Count the objects:  ... (5 dots). How many?",
    "answer_guide": "5",
    "max_level": 4
  }
]
```

## Local (IndexedDB / Dexie) mirrors

The web app mirrors these tables in IndexedDB so the UI works offline:

- `learning_areas`, `strands`, `sub_strands` — read-only cache, refreshed
  on login.
- `assessments` (templates owned by current user), `classes`,
  `learners`, `assessment_runs`, `scores` — read/write mirrors with a
  `_dirty: 0 | 1` flag and `_synced_at: timestamptz` per row. The flag
  is numeric because IndexedDB cannot index booleans — rows holding
  `true` are silently dropped from an index, so `_dirty` must be `0 | 1`
  for the sync queue queries (`where('_dirty').equals(1)`) to work.
  Dexie schema version 2 normalises any legacy boolean rows on upgrade.

A background sync worker drains dirty rows. See
`docs/06-architecture.md`.
