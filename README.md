# Zetheta Distributed Candidate Evaluation Platform

A production-grade distributed platform for real-time candidate assessments, built as a monorepo with FastAPI (Python), Next.js, Neon PostgreSQL, and Valkey.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Candidate Portal (Next.js)   Assessment Engine (Next.js)   │
│  Port: 4000                   Port: 4001 (separate app)     │
└──────────┬────────────────────────────┬─────────────────────┘
           │                            │
           └────────────┬───────────────┘
                        ▼
              ┌─────────────────┐
              │  API Gateway    │  ← SSE /api/events (real-time)
              │  (FastAPI)      │
              │  Port: 3000     │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │  Auth    │  │  arq     │  │  Valkey  │
   │ Service  │  │ Worker   │  │ (Redis)  │
   │:3001     │  │          │  │ :6379    │
   └────┬─────┘  └──────────┘  └──────────┘
        │
        ▼
   ┌──────────┐
   │   Neon   │
   │ Postgres │
   └──────────┘
```

### Components

| Component | Tech | Responsibility |
|-----------|------|---------------|
| **Candidate Portal** | Next.js 15 | Login, dashboard, "Start Assessment" trigger |
| **Assessment Engine** | Next.js 15 | Separate deployable app — MCQ interface, submission, results |
| **Employer Dashboard** | Next.js 15 | Real-time funnel, candidate list, analytics, audit trail |
| **API Gateway** | FastAPI | Unified ingress, routing, SSE hub, request validation |
| **Auth Service** | FastAPI | JWT login, cross-app opaque token mint/redeem |
| **Evaluation Worker** | Python + Redis queue | Async scoring pipeline with retry + idempotency |
| **Neon PostgreSQL** | Serverless Postgres | Primary data store with indexed hot paths |
| **Valkey** | Open-source Redis fork | Queue, pub/sub, cross-app token store |

## Key Design Decisions

### Cross-Application Token (Security-Critical)
- **Opaque tokens** generated server-side only via `secrets.token_urlsafe(32)`
- **HMAC-SHA256 binding** cryptographically ties token to `candidate_id + application_id + nonce`
- **120-second TTL** enforced by Valkey `SETEX`
- **Single-use** guaranteed by atomic `GET` + `DELETE` on redemption
- **Timing-attack safe** via `hmac.compare_digest()` for all comparisons

### Async Evaluation Pipeline
- Submissions are stored in Neon **first**, then enqueued to Valkey
- If Valkey is down, submissions are safe in Postgres; a recovery cron re-enqueues orphaned jobs
- Worker uses `_job_id = application_id` for idempotency — duplicate events never create duplicate scores
- Exponential backoff retry (max 3 attempts) with dead-letter logging

### Real-Time Updates
- **Server-Sent Events (SSE)** via FastAPI `StreamingResponse`
- Valkey pub/sub bridges worker completions to API Gateway SSE stream
- Dashboard auto-reconnects with gap-filling REST fetch on reconnect

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, Uvicorn |
| Database | Neon PostgreSQL (serverless) |
| Cache/Queue | Valkey 7.2 (open-source Redis replacement) |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Auth | PyJWT + bcrypt + `cryptography` |
| Logging | `structlog` (structured JSON) |
| Metrics | `prometheus-fastapi-instrumentator` |

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone & Configure

```bash
git clone <repo-url>
cd zetheta-platform
cp .env.example .env
# Edit .env with your Neon DATABASE_URL
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

This starts:
- Valkey on `:6379`
- Auth Service on `:3001`
- API Gateway on `:3000`
- Evaluation Worker (2 replicas)
- Candidate Portal on `:4000`
- Assessment Engine on `:4001`
- Employer Dashboard on `:4002`

### 3. Seed the Database

```bash
cd packages/shared-db
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py
```

### 4. Access the Apps

| App | URL | Credentials |
|-----|-----|-------------|
| Candidate Portal | http://localhost:4000 | alex.rivera@example.com / candidate123 |
| Assessment Engine | http://localhost:4001 | (accessed via cross-app token) |
| Employer Dashboard | http://localhost:4002 | hr@zetheta.com / admin123 |
| API Docs (Gateway) | http://localhost:3000/docs | — |
| API Docs (Auth) | http://localhost:3001/docs | — |

## API Endpoints

### Auth Service (`:3001`)
- `POST /auth/login` — Candidate/HR login → JWT
- `POST /auth/cross-app-token` — Mint short-lived cross-app token (JWT required)
- `POST /auth/redeem-cross-app` — Redeem token → assessment session JWT
- `GET /auth/verify` — Verify JWT validity

### API Gateway (`:3000`)
- `GET /api/questions` — Fetch MCQs (assessment session)
- `POST /api/submissions` — Submit assessment answers
- `GET /api/candidates` — List candidates (employer only)
- `GET /api/scores` — List scores (employer only)
- `GET /api/analytics/funnel` — Funnel counts
- `GET /api/events` — SSE real-time stream

## Cross-App Flow

```
Candidate Portal (logged in)
    │ POST /auth/cross-app-token {application_id}
    │←── {token, expires_in: 120}
    │
    │──→ Redirect to Assessment Engine?token=xxx
    │
Assessment Engine
    │ POST /auth/redeem-cross-app {token}
    │←── {session_token}
    │
    │──→ GET /api/questions (session_token)
    │←── [MCQ questions]
    │
    │──→ POST /api/submissions {answers}
    │←── {status: "submitted"}
    │
    Worker evaluates → Dashboard updates via SSE
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Candidates & employers (bcrypt passwords) |
| `applications` | Assessment sessions (status tracking) |
| `mcq_questions` | Question bank with options & correct answers |
| `responses` | Per-question candidate answers |
| `scores` | Computed results (unique per application) |
| `pending_evaluations` | Recovery queue for Redis downtime |

### Indexed Hot Paths
- `users(email)` — login
- `applications(candidate_id, status)` — per-candidate history
- `applications(status, submitted_at)` — dashboard filtering
- `responses(application_id)` — scoring lookup
- `scores(application_id)` — idempotency + one-score guarantee

## Security

- No secrets committed — all via `.env`
- Input validation on every endpoint (Pydantic v2 / Zod)
- Cross-app tokens: cryptographically random, HMAC-bound, 120s TTL, single-use
- Passwords hashed with `bcrypt`
- JWTs with `exp` claim and type scoping (`access` / `refresh` / `assessment_session`)
- Containers run as non-root (`UID 1001`)
- Run `pip-audit` and `npm audit` before deployment

## Testing

```bash
# Backend tests
cd services/auth-service && pytest

# Load test
pip install locust
locust -f load_test.py --host http://localhost:3000
```

## Deployment

### Docker Compose (Local — Required)
```bash
docker compose up
```

### Vercel (Frontend Bonus)
Each Next.js app can be deployed independently to Vercel:
```bash
cd apps/candidate-portal && vercel --prod
```

## Observability

- **Structured logs**: JSON format with `service`, `trace_id`, `duration_ms`
- **Metrics**: `/metrics` endpoint exposes p95 latency, job success/failure rates
- **Health checks**: `/health` on all services

## License

Built for Zetheta Internship Selection Assignment — 2025.
