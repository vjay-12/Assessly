# Schema Design Document

## Entities & Relationships

```
User ||--o{ Application : submits
Application ||--o{ Response : contains
Application ||--|| Score : receives
MCQQuestion ||--o{ Response : answered_in
```

## Table Definitions

### users
Stores both candidates and employers. Distinguished by `role` enum.

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX |
| name | VARCHAR(255) | NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| role | ENUM | candidate / employer |
| status | ENUM | applied / active / archived |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | AUTO UPDATE |

**Indexes:**
- `ix_users_status_created` — funnel aggregation queries
- `ix_users_email` — implicit via UNIQUE

### applications
Links candidates to assessment sessions. Status tracks funnel progression.

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | FK → users.id, INDEX |
| status | ENUM | applied → attempted → submitted → evaluated |
| started_at | TIMESTAMPTZ | NULLABLE |
| submitted_at | TIMESTAMPTZ | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Indexes:**
- `ix_applications_candidate_status` — per-candidate history
- `ix_applications_status_submitted` — dashboard filter by status + recency
- `ix_applications_created` — pagination

### mcq_questions
Question bank for assessments.

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| question_text | TEXT | NOT NULL |
| options | TEXT[] | PostgreSQL array, NOT NULL |
| correct_option | INTEGER | NOT NULL (0-based index) |
| difficulty | INTEGER | DEFAULT 1 |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Indexes:**
- `ix_questions_difficulty` — filter by difficulty

### responses
Per-question candidate answers. Unique constraint prevents duplicate answers.

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| application_id | UUID | FK → applications.id, INDEX |
| question_id | UUID | FK → mcq_questions.id, INDEX |
| selected_option | INTEGER | NOT NULL |
| is_correct | BOOLEAN | NOT NULL |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Indexes:**
- `ix_responses_application` — fetch all answers for scoring
- `ix_responses_question` — question-level analytics
- `ix_responses_app_question` UNIQUE — prevents duplicate answers

### scores
One score per application. Unique constraint enforces idempotency.

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| application_id | UUID | FK, UNIQUE — one score per app |
| total_questions | INTEGER | NOT NULL |
| correct_count | INTEGER | NOT NULL |
| percentage | FLOAT | NOT NULL |
| evaluated_at | TIMESTAMPTZ | DEFAULT now() |
| worker_id | VARCHAR(100) | NOT NULL — observability |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Indexes:**
- `ix_scores_percentage` — filter by score range
- `ix_scores_evaluated` — sort by recency

### pending_evaluations
Recovery table for Redis/Valkey downtime scenarios.

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| application_id | UUID | FK, INDEX |
| queued_at | TIMESTAMPTZ | DEFAULT now() |

## Index Strategy Justification

| Index | Hot Query |
|-------|-----------|
| `users(email)` | Every login |
| `users(status, created_at)` | "How many candidates this week?" |
| `applications(status, submitted_at)` | Dashboard main list filter |
| `responses(application_id)` | Worker scoring lookup |
| `scores(application_id)` UNIQUE | Idempotency check |

All queries use indexed lookups. No full table scans on hot paths.
