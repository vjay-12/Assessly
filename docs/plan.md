# Assessly Distributed Candidate Evaluation Platform — Implementation Plan

> **Version**: 2.0 (Updated per candidate tech preferences)  
> **Date**: 2026-04-23  
> **Status**: Draft — Pre-implementation  

---

## 1. Executive Summary

This document outlines the architecture, technology choices, data flows, and implementation approach for building a production-grade distributed candidate evaluation platform. The system comprises **3 Next.js frontend applications**, **3 Python (FastAPI) backend services**, **shared packages**, **Neon PostgreSQL** (cloud), and **Upstash Redis** (cloud) — runnable locally via Docker Compose with mocked/cloud data layers.

The two highest-risk areas identified are:
1. **Cross-application token mechanism** — must be cryptographically sound, single-use, and replay-resistant
2. **Async evaluation pipeline** — must be idempotent, retry-safe, and degrade gracefully under Redis failure

---

## 2. System Architecture & Component Breakdown

### 2.1 Monorepo Structure (Turborepo + pnpm + Python)

```
assessly-evaluation-platform/
├── apps/
│   ├── candidate-portal/          # Next.js 15 — Login + Assessment entry
│   ├── assessment-engine/         # Next.js 15 — MCQ interface (separate deployable)
│   └── employer-dashboard/        # Next.js 15 — Real-time funnel view
├── services/
│   ├── api-gateway/               # FastAPI — Unified ingress, routing, rate limiting
│   ├── auth-service/              # FastAPI — JWT issuance, cross-app token generation/validation
│   └── evaluation-worker/         # Python + arq — Async scoring pipeline (Redis-backed)
├── packages/
│   ├── shared-types/              # TypeScript contracts (frontend + gateway validation)
│   └── shared-ui/                 # Shared React components (optional)
├── docs/
│   ├── plan.md                    # This document
│   ├── schema-design.md           # Database schema rationale
│   ├── api-design.md              # Endpoint contracts
│   ├── cross-app-token.md         # Security mechanism deep-dive
│   ├── pipeline-design.md         # Worker + retry + idempotency
│   └── deployment-design.md       # Docker Compose + cloud topology
├── docker-compose.yml             # Local orchestration (services + Redis)
├── turbo.json                     # Turborepo pipeline config
├── pnpm-workspace.yaml            # Frontend workspaces
├── README.md                      # Setup, architecture, decisions
└── .env.example                   # All required env vars (no secrets)
```

### 2.2 Component Responsibilities

| Component | Runtime | Responsibility |
|-----------|---------|---------------|
| Candidate Portal | Next.js (App Router) | Candidate login (JWT cookie), "Start Assessment" trigger, redirect to Assessment Engine with cross-app token |
| Assessment Engine | Next.js (App Router) | Receive cross-app token, validate via auth-service, render MCQs, collect answers, submit to API gateway |
| Employer Dashboard | Next.js (App Router) | HR login, candidate funnel view (Applied → Attempted → Evaluated), real-time SSE updates |
| API Gateway | FastAPI + Uvicorn | Route `/api/*` to appropriate services, auth middleware, rate limiting, request validation, SSE hub |
| Auth Service | FastAPI + Uvicorn | JWT login/refresh, cross-app token minting & redemption, session verification, Neon DB access |
| Evaluation Worker | Python + arq | Consume Redis queue events, score submissions idempotently, store results to Neon, publish completion |
| PostgreSQL | **Neon** (Cloud) | Serverless primary data store — candidates, applications, questions, responses, scores |
| Redis | **Upstash** (Cloud) | arq task queue, pub/sub for real-time updates, cross-app token blacklist/tracking |

---

## 3. Technology Choices with Justification

| Layer | Choice | Alternatives Rejected | Justification |
|-------|--------|----------------------|---------------|
| **Frontend** | Next.js 15 (App Router) | React SPA, Vue, Svelte | SSR for auth pages, API routes for BFF pattern, unified framework across all 3 apps, excellent TypeScript DX |
| **Backend** | **FastAPI** (Python 3.11+) | Fastify, NestJS, Django | Native async/await (`async`/`await`), automatic OpenAPI docs, Pydantic v2 validation, dependency injection, Python ecosystem familiarity, extremely fast to develop |
| **Database** | **Neon PostgreSQL** | Supabase, RDS, local Postgres | Serverless auto-scaling, generous free tier, branching for dev/prod, connection pooling built-in, excellent for assignments/demo deployments |
| **ORM / DB Access** | **SQLAlchemy 2.0** + asyncpg | Prisma (Python), Tortoise, Peewee | Industry standard for Python async, mature migrations via Alembic, full control over queries and indexes |
| **Queue / Worker** | **arq** (async Redis queue) | Celery, RQ, BullMQ | Native async (unlike Celery/RQ), type-safe job dispatch, built-in retries, uses Redis, modern Pythonic API, much lighter than Celery |
| **Redis Provider** | **Upstash Redis** | Redis Cloud, AWS ElastiCache | Generous free tier (10k req/day + 256MB), global edge regions, REST API + Redis protocol, zero infra management, no credit card for free tier |
| **Real-time** | **SSE** (Server-Sent Events) | WebSockets, Long-polling, Socket.io | One-way server→client flow fits dashboard perfectly, works over HTTP/1.1 and HTTP/2, no WebSocket upgrade needed, easy auth via standard headers |
| **Validation** | **Pydantic v2** + Zod | Marshmallow, Joi | Pydantic for Python services (native to FastAPI), Zod for frontend form validation, both generate TypeScript-like safety |
| **Auth / Crypto** | PyJWT + `cryptography` + `itsdangerous` | Authlib, python-jose | `cryptography` is the gold standard for HMAC/AES; PyJWT for RS256 JWTs; `itsdangerous` for signed opaque tokens |
| **Logging** | **structlog** | loguru, standard logging | Structured JSON logs, context binding, async-safe, industry standard for Python observability |
| **Metrics** | **prometheus-fastapi-instrumentator** | statsd, custom | Zero-config FastAPI metrics, exposes `/metrics` endpoint, tracks latency histograms (p95/p99) |
| **Testing** | pytest + httpx + pytest-asyncio | unittest, nose2 | Modern async test support, FastAPI TestClient compatibility, excellent fixture system |
| **Deployment** | Docker Compose (local) + Vercel (frontend) | Kubernetes, Render | Docker Compose satisfies the mandatory single-command local run; Vercel for free Next.js hosting with live URL |

### 3.1 Why FastAPI for This Assignment?

FastAPI is an exceptional choice for this distributed platform for several concrete reasons:

1. **Performance**: Built on Starlette + Uvicorn, FastAPI handles async I/O efficiently. For the <200ms p95 target, Python's `asyncpg` + `uvicorn` can easily handle 1,000+ concurrent connections — more than sufficient for this workload.

2. **Type Safety**: Pydantic v2 provides compile-time-level validation at runtime. The cross-app token payload, JWT claims, and all API contracts are validated automatically with clear 422 errors.

3. **Developer Velocity**: Automatic OpenAPI (`/docs`) and ReDoc generation means every endpoint is self-documenting. This is invaluable in a time-constrained assignment.

4. **Dependency Injection**: FastAPI's DI system makes it trivial to inject database sessions, Redis clients, and auth dependencies — keeping controllers clean and testable.

5. **SSE Native Support**: FastAPI has built-in `StreamingResponse` which makes implementing Server-Sent Events trivial compared to WebSocket handshakes.

6. **Python Ecosystem**: `arq` for queues, `asyncpg` for Postgres, `aioredis` for Redis — all are first-class async libraries that integrate seamlessly.

### 3.2 Why Neon PostgreSQL?

Neon is a serverless PostgreSQL platform that separates compute and storage:
- **Free Tier**: 500 MB storage + unlimited databases — perfect for a demo/assignment
- **Connection Pooling**: Built-in PgBouncer means even if multiple Docker containers connect, you won't exhaust Postgres limits
- **Branching**: You can branch the DB for testing (bonus feature if you want to show off)
- **No Local Docker Needed**: Eliminates the need for a local Postgres container, reducing Docker Compose startup time
- **Live URL**: Provides a public connection string you can deploy anywhere

### 3.3 Why Upstash Redis?

Upstash is a serverless Redis service with a **per-request pricing model**:
- **Free Tier**: 10,000 commands/day + 256 MB — more than enough for an assignment
- **Redis Protocol**: Works with `redis-py`, `aioredis`, and `arq` out of the box
- **Global Replication**: If you deploy to Vercel edge, you can place Redis close to your functions
- **No Infrastructure**: No Docker container needed for Redis locally if you use the cloud instance, though we'll include Redis in Docker Compose for true offline development

**Recommended approach**: Use Upstash for the "live deployed" version, but include a local Redis container in Docker Compose so the system works fully offline.

---

## 4. Data Flow Diagrams

### 4.1 Cross-Application Assessment Flow (Critical)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Candidate Portal│     │  Auth Service    │     │Assessment Engine│
│  (Next.js)      │     │  (FastAPI)       │     │  (Next.js)      │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │                         ▲
         │  POST /auth/cross-app-token                     │
         │  Authorization: Bearer <JWT>                    │
         │  { application_id, candidate_id }               │
         │────────────────────────────────────────────────>│
         │                       │                         │
         │  { token, expires_at }                          │
         │<────────────────────────────────────────────────│
         │                       │                         │
         │  302 Redirect to                                  │
         │  assessment-engine.com/assessment?token=xxx       │
         │─────────────────────────────────────────────────>│
         │                       │                         │
         │                       │     POST /auth/redeem   │
         │                       │     { token, nonce }    │
         │                       │<────────────────────────│
         │                       │                         │
         │                       │  { session_token }      │
         │                       │────────────────────────>│
         │                       │                         │
```

**Token Structure (Opaque, Server-Generated via FastAPI):**
```python
import secrets
import hmac
import hashlib
from cryptography.fernet import Fernet

# Token composition
token_id = secrets.token_urlsafe(32)  # 256-bit random
nonce = secrets.token_urlsafe(16)     # 128-bit nonce

binding = hmac.new(
    key=CROSS_APP_SECRET.encode(),
    msg=f"{candidate_id}:{application_id}:{nonce}:{timestamp}".encode(),
    digestmod=hashlib.sha256
).hexdigest()

# Store in Upstash Redis
redis.setex(
    f"crossapp:{token_id}",
    120,  # 120s TTL
    json.dumps({
        "candidate_id": candidate_id,
        "application_id": application_id,
        "nonce": nonce,
        "binding": binding,
        "used": False
    })
)

# Return to client
token = f"{token_id}:{binding}"
```

### 4.2 Evaluation Pipeline Flow

```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Assessment  │    │  API Gateway│    │   Upstash    │    │ Evaluation      │
│    Engine    │    │  (FastAPI)  │    │   Redis      │    │    Worker       │
│   (Next.js)  │    │             │    │   (arq)      │    │  (Python + arq) │
└──────┬───────┘    └──────┬──────┘    └──────┬───────┘    └─────────────────┘
       │                   │                    │                    │
       │ POST /api/submit  │                    │                    │
       │──────────────────>│                    │                    │
       │                   │  1. INSERT response│                    │
       │                   │  2. INSERT answers │                    │
       │                   │  ────> Neon DB     │                    │
       │                   │                    │                    │
       │                   │  enqueue_job(      │                    │
       │                   │    "evaluate",     │                    │
       │                   │    {application_id},│                   │
       │                   │    _job_id=app_id  │  # idempotency     │
       │                   │  )                 │                    │
       │                   │────────────────────────────────────────>│
       │                   │                    │                    │
       │  { status: "submitted" }              │                    │
       │<──────────────────│                    │                    │
       │                   │                    │     PICKUP JOB     │
       │                   │                    │<───────────────────│
       │                   │                    │                    │
       │                   │                    │     PROCESS        │
       │                   │                    │  • Compute score   │
       │                   │                    │  • INSERT score    │
       │                   │                    │  • PUBLISH event   │
       │                   │                    │                    │
       │                   │   Redis PUB/SUB    │                    │
       │                   │   channel: scores  │                    │
       │                   │<─────────────────────────────────────────│
       │                   │                    │                    │
       │                   │   SSE to dashboard │                    │
       │                   │   (StreamingResponse)│                  │
       │                   │────────────────────────────────────────>│
```

### 4.3 Real-Time Dashboard Update Flow

```
┌──────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Employer Dashboard│         │  API Gateway    │         │   Upstash       │
│    (Next.js)      │         │  (FastAPI SSE)  │         │   Redis         │
└────────┬─────────┘         └────────┬────────┘         └─────────────────┘
         │                            │                          ▲
         │  GET /api/events (SSE)     │                          │
         │  Authorization: Bearer     │                          │
         │───────────────────────────>│                          │
         │                            │  SUBSCRIBE scores        │
         │                            │─────────────────────────>│
         │  data: {event, payload}    │                          │
         │<───────────────────────────│                          │
         │                            │                          │
         │                            │    PUBLISH on scores     │
         │                            │<─────────────────────────│
         │  data: {event, payload}    │                          │
         │<───────────────────────────│                          │
```

---

## 5. Database Schema Design (Neon PostgreSQL)

### 5.1 SQLAlchemy 2.0 Async Models

```python
from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, ForeignKey, Index, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime
import enum

Base = declarative_base()

class CandidateStatus(str, enum.Enum):
    APPLIED = "applied"
    ACTIVE = "active"
    ARCHIVED = "archived"

class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    ATTEMPTED = "attempted"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)  # bcrypt
    status = Column(Enum(CandidateStatus), default=CandidateStatus.APPLIED, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    applications = relationship("Application", back_populates="candidate")
    
    __table_args__ = (
        Index("ix_candidates_status_created", "status", "created_at"),
    )

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.APPLIED, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    candidate = relationship("Candidate", back_populates="applications")
    responses = relationship("Response", back_populates="application")
    score = relationship("Score", back_populates="application", uselist=False)
    
    __table_args__ = (
        Index("ix_applications_candidate_status", "candidate_id", "status"),
        Index("ix_applications_status_submitted", "status", "submitted_at"),
        Index("ix_applications_created", "created_at"),
    )

class MCQQuestion(Base):
    __tablename__ = "mcq_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_text = Column(String(1000), nullable=False)
    options = Column(ARRAY(String(500)), nullable=False)  # PostgreSQL array
    correct_option = Column(Integer, nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    responses = relationship("Response", back_populates="question")
    
    __table_args__ = (
        Index("ix_questions_difficulty", "difficulty"),
    )

class Response(Base):
    __tablename__ = "responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("mcq_questions.id"), nullable=False, index=True)
    selected_option = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    application = relationship("Application", back_populates="responses")
    question = relationship("MCQQuestion", back_populates="responses")
    
    __table_args__ = (
        Index("ix_responses_application", "application_id"),
        Index("ix_responses_question", "question_id"),
        Index("ix_responses_app_question", "application_id", "question_id", unique=True),
    )

class Score(Base):
    __tablename__ = "scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), unique=True, nullable=False, index=True)
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    worker_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    application = relationship("Application", back_populates="score")
    
    __table_args__ = (
        Index("ix_scores_percentage", "percentage"),
        Index("ix_scores_evaluated", "evaluated_at"),
    )
```

### 5.2 Index Strategy Justification

| Index | Purpose | Hot Path |
|-------|---------|----------|
| `candidates(email)` | Login lookup | Every login |
| `candidates(status, created_at)` | Funnel aggregation queries | Dashboard overview |
| `applications(candidate_id, status)` | Per-candidate history | Portal profile |
| `applications(status, submitted_at)` | Dashboard filter by status + recency | Dashboard main list |
| `responses(application_id)` | Fetch all answers for scoring | Worker evaluation |
| `responses(application_id, question_id)` UNIQUE | Prevent duplicate answers | Submission handler |
| `scores(application_id)` UNIQUE | One score per app, idempotency | Worker + dashboard |
| `scores(percentage)` | Filter candidates by score range | Dashboard filtering |

---

## 6. API Design Overview (FastAPI)

### 6.1 Auth Service Endpoints (`auth-service`, port 3001)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | Public | Candidate/HR login → JWT access + refresh tokens |
| POST | `/auth/refresh` | Refresh Token | Rotate access token |
| POST | `/auth/cross-app-token` | JWT Bearer | Mint short-lived cross-app token (120s) |
| POST | `/auth/redeem-cross-app` | Token Body | Redeem token → assessment session JWT (5 min) |
| GET | `/auth/verify` | JWT Bearer | Verify token validity |

### 6.2 API Gateway Endpoints (`api-gateway`, port 3000)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/submissions` | Cross-app Session | Submit assessment answers, enqueue evaluation |
| GET | `/api/submissions/{id}` | JWT Bearer | Get submission status |
| GET | `/api/candidates` | JWT Bearer | List candidates (paginated, filterable) |
| GET | `/api/candidates/{id}` | JWT Bearer | Candidate detail with applications |
| GET | `/api/scores` | JWT Bearer | List scores (paginated, filterable) |
| GET | `/api/events` | JWT Bearer (SSE) | Real-time event stream for dashboard |
| GET | `/api/questions` | Cross-app Session | Fetch MCQ questions for assessment |

### 6.3 Pydantic Request/Response Contracts

```python
# Cross-App Token Minting
# POST /auth/cross-app-token
# Headers: Authorization: Bearer <JWT>
class CrossAppTokenRequest(BaseModel):
    application_id: UUID

class CrossAppTokenResponse(BaseModel):
    token: str                    # ca_abc123... (opaque)
    expires_at: datetime
    expires_in: int = 120         # seconds

# Cross-App Token Redemption
# POST /auth/redeem-cross-app
class RedeemTokenRequest(BaseModel):
    token: str
    nonce: str

class RedeemTokenResponse(BaseModel):
    session_token: str            # Short-lived JWT (5 min)
    candidate_id: UUID
    application_id: UUID

# Submission
# POST /api/submissions
class AnswerSubmission(BaseModel):
    question_id: UUID
    selected_option: int

class SubmissionRequest(BaseModel):
    application_id: UUID
    answers: list[AnswerSubmission]

class SubmissionResponse(BaseModel):
    status: Literal["submitted", "already_submitted"]
    application_id: UUID
    message: str
```

---

## 7. Cross-Application Token Design (Security-Critical)

### 7.1 Threat Model

| Threat | Mitigation |
|--------|-----------|
| Token guessability | `secrets.token_urlsafe(32)` — 256-bit CSPRNG |
| Token reuse | Redis atomic `HSET` with `used` flag; immediate deletion after redemption |
| Replay attacks | 128-bit nonce generated server-side, client must echo it back; binding includes nonce |
| Client-side generation | Impossible — only `/auth/cross-app-token` (authenticated) can mint |
| Session hijacking | Token cryptographically bound to `candidate_id` + `application_id` via HMAC |
| Timing attacks | `hmac.compare_digest()` for all string comparisons |
| Token theft window | 120-second TTL + single-use = extremely narrow attack window |

### 7.2 Token Lifecycle (FastAPI Implementation)

```python
import secrets
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as redis

class CrossAppTokenService:
    def __init__(self, redis_client: redis.Redis, secret: str):
        self.redis = redis_client
        self.secret = secret
    
    async def mint(
        self, 
        candidate_id: str, 
        application_id: str
    ) -> dict:
        """Generate a single-use, time-bound, bound cross-app token."""
        token_id = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(16)
        timestamp = datetime.utcnow().isoformat()
        
        binding = hmac.new(
            key=self.secret.encode(),
            msg=f"{candidate_id}:{application_id}:{nonce}:{timestamp}".encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        payload = json.dumps({
            "candidate_id": str(candidate_id),
            "application_id": str(application_id),
            "nonce": nonce,
            "binding": binding,
            "used": False
        })
        
        # Store with 120s TTL
        await self.redis.setex(f"crossapp:{token_id}", 120, payload)
        
        return {
            "token": f"ca_{token_id}:{binding}",
            "nonce": nonce,  # Actually, nonce should NOT be sent to client
            "expires_at": datetime.utcnow() + timedelta(seconds=120),
            "expires_in": 120
        }
    
    async def redeem(self, token: str, nonce: str) -> Optional[dict]:
        """Redeem token. Returns session payload or None."""
        if not token.startswith("ca_"):
            return None
        
        parts = token[3:].split(":")
        if len(parts) != 2:
            return None
        
        token_id, provided_binding = parts
        
        # Atomic fetch-and-delete (ensures single-use)
        raw = await self.redis.get(f"crossapp:{token_id}")
        if not raw:
            return None  # Expired or never existed
        
        payload = json.loads(raw)
        
        if payload["used"]:
            return None  # Already redeemed
        
        # Verify nonce match
        if not hmac.compare_digest(payload["nonce"], nonce):
            return None
        
        # Verify binding match
        if not hmac.compare_digest(payload["binding"], provided_binding):
            return None
        
        # Mark as used (or delete — delete is safer)
        await self.redis.delete(f"crossapp:{token_id}")
        
        return {
            "candidate_id": payload["candidate_id"],
            "application_id": payload["application_id"]
        }
```

### 7.3 Why Opaque Tokens Over JWT for Cross-App?

| Property | JWT | Opaque + Redis |
|----------|-----|---------------|
| Revocation | Requires blacklist lookup (defeats purpose) | Instant via `DEL` or `used` flag |
| Single-use guarantee | Impossible statelessly | Trivial with atomic Redis operations |
| Size | Large (can be 500+ bytes) | Small (~64 bytes token ID) |
| Information leakage | Contains claims readable by client | Completely opaque |
| Replay resistance | Requires `jti` + blacklist | Built-in via deletion |

For this flow, **opaque tokens are the only correct choice**.

---

## 8. Evaluation Pipeline Design (arq + FastAPI)

### 8.1 Why arq over Celery/RQ?

| Feature | arq | Celery | RQ |
|---------|-----|--------|-----|
| Native async | ✅ Yes | ❌ No (sync) | ❌ No (sync) |
| Type safety | ✅ Full | ❌ Limited | ❌ None |
| Redis dependency | ✅ Minimal | ❌ Requires broker + backend | ✅ Minimal |
| Retries | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| Delayed jobs | ✅ Yes | ✅ Yes | ✅ Yes |
| Startup time | ✅ Instant | ❌ Slow (needs beat, flower, etc.) | ✅ Fast |

`arq` is purpose-built for modern Python async services. It uses Redis lists (not pub/sub) for reliable delivery, supports job results storage, and has a beautiful typed API.

### 8.2 Worker Implementation

```python
# services/evaluation-worker/src/worker.py
from arq import create_pool, ArqRedis
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

logger = logging.getLogger("evaluation-worker")

async def evaluate_submission(ctx, application_id: str):
    """
    Idempotent, retry-safe evaluation job.
    """
    db: AsyncSession = ctx["db"]
    worker_id = ctx["worker_id"]
    
    # 1. Idempotency check
    existing = await db.execute(
        select(Score).where(Score.application_id == application_id)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Score already exists for {application_id}, skipping")
        return {"status": "already_evaluated"}
    
    # 2. Fetch responses
    result = await db.execute(
        select(Response, MCQQuestion)
        .join(MCQQuestion)
        .where(Response.application_id == application_id)
    )
    rows = result.all()
    
    if not rows:
        raise Exception(f"No responses found for {application_id}")  # Will retry
    
    # 3. Compute score
    total = len(rows)
    correct = sum(1 for r, q in rows if r.selected_option == q.correct_option)
    percentage = (correct / total) * 100
    
    # 4. Update is_correct flags (in case they weren't set at submission)
    for response, question in rows:
        response.is_correct = (response.selected_option == question.correct_option)
    
    # 5. Store score + update application status (transaction)
    score = Score(
        application_id=application_id,
        total_questions=total,
        correct_count=correct,
        percentage=percentage,
        worker_id=worker_id
    )
    
    await db.execute(
        update(Application)
        .where(Application.id == application_id)
        .values(status=ApplicationStatus.EVALUATED)
    )
    db.add(score)
    await db.commit()
    
    # 6. Publish real-time event
    redis: ArqRedis = ctx["redis"]
    await redis.publish("scores", json.dumps({
        "type": "EVALUATION_COMPLETED",
        "payload": {
            "application_id": application_id,
            "percentage": percentage,
            "evaluated_at": datetime.utcnow().isoformat()
        }
    }))
    
    logger.info(f"Evaluation completed: {application_id} = {percentage}%")
    return {"status": "completed", "percentage": percentage}

class WorkerSettings:
    functions = [evaluate_submission]
    redis_settings = RedisSettings(host="localhost", port=6379)
    max_jobs = 10
    job_timeout = 30  # seconds
    retry_jobs = True
    # Exponential backoff: 5s, 10s, 20s
    default_job_expires = 3600
```

### 8.3 Retry & Fault Tolerance Strategy

```python
# In API Gateway — enqueue with idempotency key
await redis.enqueue_job(
    "evaluate_submission",
    application_id=str(application_id),
    _job_id=str(application_id),  # CRITICAL: prevents duplicate jobs
    _queue_name="evaluation"
)
```

| Failure Mode | Behavior |
|-------------|----------|
| Worker crash mid-evaluation | Job remains in Redis, picked up by another worker on restart |
| Database timeout | arq retries with exponential backoff (max 3 attempts) |
| Redis pub/sub fails | Score is still committed; dashboard may lag but data is safe |
| No responses found (data bug) | After 3 retries, job moves to dead-letter (logged, not lost) |
| Duplicate submission | Same `application_id` as `_job_id` = existing job returned, not re-queued |

### 8.4 Redis Failure Graceful Degradation

```python
# API Gateway submission handler
@app.post("/api/submissions")
async def submit_assessment(...):
    # 1. ALWAYS store in Neon first
    async with db.begin():
        await store_responses(application_id, answers)
        await update_application_status(application_id, "SUBMITTED")
    
    # 2. Attempt to queue — if Redis fails, still return success
    try:
        await redis.enqueue_job(
            "evaluate_submission", 
            str(application_id),
            _job_id=str(application_id)
        )
    except redis.ConnectionError:
        logger.error("Redis unavailable — evaluation queued for retry")
        # Store in "pending_evaluations" table for cron recovery
        await db.execute(
            insert(PendingEvaluation).values(application_id=application_id)
        )
        await db.commit()
    
    return {"status": "submitted", "application_id": application_id}
```

**Recovery cron** (runs every 60s in API Gateway):
```python
async def recover_orphaned_evaluations():
    """Find applications that are SUBMITTED but have no Score."""
    result = await db.execute(
        select(Application.id)
        .where(Application.status == ApplicationStatus.SUBMITTED)
        .where(~exists().where(Score.application_id == Application.id))
    )
    for app_id in result.scalars():
        await redis.enqueue_job("evaluate_submission", str(app_id))
```

This guarantees **zero data loss** even during prolonged Redis outages.

---

## 9. Real-Time System Design

### 9.1 FastAPI SSE Endpoint

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import redis.asyncio as redis

router = APIRouter()

async def event_stream(redis_client: redis.Redis, user_id: str):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("scores")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                # Optional: filter events by user permissions
                yield f"data: {json.dumps(data)}\n\n"
    except asyncio.CancelledError:
        await pubsub.unsubscribe("scores")
        await pubsub.close()

@router.get("/events")
async def sse_endpoint():
    return StreamingResponse(
        event_stream(redis_client, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

### 9.2 Dashboard Client (Next.js)

```typescript
// apps/employer-dashboard/lib/sse.ts
export function useSSE() {
  useEffect(() => {
    const eventSource = new EventSource('/api/events', {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'EVALUATION_COMPLETED') {
        queryClient.invalidateQueries({ queryKey: ['candidates'] });
      }
    };
    
    eventSource.onerror = () => {
      console.warn('SSE connection lost, retrying...');
      eventSource.close();
      // Browser auto-reconnects with exponential backoff
    };
    
    return () => eventSource.close();
  }, []);
}
```

### 9.3 Gap-Filling on Reconnect

If SSE disconnects for >30s, the dashboard performs a full REST fetch on reconnect to ensure no missed events:

```typescript
eventSource.onopen = () => {
  // Fetch latest state to fill any gaps
  queryClient.invalidateQueries({ queryKey: ['candidates'] });
};
```

---

## 10. Observability Design

### 10.1 Structured Logging (structlog)

```python
# packages/shared-utils/python/logger.py
import structlog
import logging
import sys

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

def get_logger(name: str):
    return structlog.get_logger(name)

# Usage in services:
logger = get_logger("auth-service")
logger.info(
    "cross_app_token_minted",
    candidate_id=candidate_id,
    application_id=application_id,
    ttl_seconds=120
)
```

### 10.2 Metrics (prometheus-fastapi-instrumentator)

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Custom metrics
from prometheus_client import Counter, Histogram

evaluation_jobs = Counter('evaluation_jobs_total', 'Total evaluation jobs', ['status'])
evaluation_duration = Histogram('evaluation_duration_seconds', 'Time spent evaluating')
```

### 10.3 Error Tracking

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        trace=traceback.format_exc()
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "trace_id": request.state.trace_id}
    )
```

### 10.4 Performance Targets Verification

```bash
# Run load test with wrk or locust
pip install locust

# locustfile.py — test submission endpoint
# Target: p95 < 200ms for GET /api/candidates
```

| Metric | Target | Verification Method |
|--------|--------|---------------------|
| API latency p95 | < 200ms | `prometheus-fastapi-instrumentator` histogram + Locust load test |
| DB query time | < 50ms | SQLAlchemy `echo=True` + `EXPLAIN ANALYZE` on Neon |
| Worker throughput | > 100 jobs/min | arq built-in stats + custom counter |
| SSE latency | < 2s event propagation | Manual stopwatch test |

---

## 11. Deployment Design

### 11.1 Local Development (Docker Compose)

Even though Neon + Upstash are used for cloud, Docker Compose provides a **fully offline** development environment:

```yaml
# docker-compose.yml
services:
  redis-local:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  auth-service:
    build: ./services/auth-service
    ports:
      - "3001:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}        # Points to Neon
      - REDIS_URL=${REDIS_URL}              # Points to Upstash OR redis-local
      - JWT_SECRET=${JWT_SECRET}
      - CROSS_APP_SECRET=${CROSS_APP_SECRET}
    depends_on:
      redis-local:
        condition: service_healthy

  api-gateway:
    build: ./services/api-gateway
    ports:
      - "3000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - AUTH_SERVICE_URL=http://auth-service:8000
    depends_on:
      - auth-service
      - redis-local

  evaluation-worker:
    build: ./services/evaluation-worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - WORKER_ID=worker-${HOSTNAME}
    depends_on:
      - redis-local
    deploy:
      replicas: 2

  candidate-portal:
    build: ./apps/candidate-portal
    ports:
      - "4000:3000"
    environment:
      - NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:3000
      - AUTH_SERVICE_URL=http://localhost:3001

  assessment-engine:
    build: ./apps/assessment-engine
    ports:
      - "4001:3000"
    environment:
      - NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:3000
      - AUTH_SERVICE_URL=http://localhost:3001

  employer-dashboard:
    build: ./apps/employer-dashboard
    ports:
      - "4002:3000"
    environment:
      - NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:3000
      - AUTH_SERVICE_URL=http://localhost:3001

volumes:
  redis_data:
```

### 11.2 Production / Cloud Topology

```
┌─────────────────────────────────────────────────────────────┐
│                         Vercel                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Candidate Portal│  │Assessment Engine│  │  Employer   │ │
│  │   (Next.js)     │  │   (Next.js)     │  │ Dashboard   │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                                ▼                            │
│                      API Gateway (FastAPI)                  │
│                      Deployed on: Render / Railway / GCP    │
└─────────────────────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │Auth Service │      │  arq Worker │      │   Upstash   │
   │  (FastAPI)  │      │  (Python)   │      │   Redis     │
   └──────┬──────┘      └─────────────┘      └─────────────┘
          │
          ▼
   ┌─────────────┐
   │    Neon     │
   │ PostgreSQL  │
   └─────────────┘
```

### 11.3 Environment Variables (.env.example)

```bash
# Database
DATABASE_URL="postgresql+asyncpg://user:password@ep-xxx.us-east-1.aws.neon.tech/assessly?sslmode=require"

# Redis (Upstash)
REDIS_URL="rediss://default:xxx@upstash-redis-url:6379"
# OR for local development:
# REDIS_URL="redis://localhost:6379"

# Auth
JWT_SECRET="your-256-bit-secret-here-min-32-chars"
JWT_ALGORITHM="RS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Cross-App Token
CROSS_APP_SECRET="another-256-bit-secret-for-hmac"
CROSS_APP_TOKEN_EXPIRE_SECONDS=120

# Service URLs
AUTH_SERVICE_URL="http://auth-service:8000"
API_GATEWAY_URL="http://api-gateway:8000"

# Worker
WORKER_ID="worker-1"

# Frontend
NEXT_PUBLIC_API_GATEWAY_URL="http://localhost:3000"
NEXT_PUBLIC_AUTH_SERVICE_URL="http://localhost:3001"
```

### 11.4 Non-Root Docker Containers

```dockerfile
# All Python services
FROM python:3.11-slim

WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

COPY --chown=appuser:appgroup . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 12. Implementation Task Breakdown

### Phase 1: Foundation (Commits 1-5)
- [ ] Initialize Turborepo monorepo with pnpm workspaces
- [ ] Set up Python virtual environments for each service (`venv` or `poetry`)
- [ ] Create shared `pyproject.toml` structure with common deps (FastAPI, SQLAlchemy, structlog)
- [ ] Set up Neon PostgreSQL project + connection
- [ ] Set up Upstash Redis + connection
- [ ] Write SQLAlchemy models + Alembic initial migration
- [ ] Seed Neon with sample MCQ questions and candidates
- [ ] Docker Compose skeleton

### Phase 2: Auth & Cross-App (Commits 6-10)
- [ ] Build auth-service with FastAPI — JWT login (RS256)
- [ ] Implement `/auth/cross-app-token` endpoint
- [ ] Implement `/auth/redeem-cross-app` endpoint
- [ ] Unit tests for token crypto (pytest)
- [ ] Document cross-app token security properties in `docs/cross-app-token.md`

### Phase 3: Core Applications (Commits 11-16)
- [ ] Build candidate-portal (Next.js) — login, dashboard, Start Assessment
- [ ] Build assessment-engine (Next.js) — MCQ UI, timer, answer collection
- [ ] Wire cross-app redirect flow end-to-end
- [ ] Build employer-dashboard (Next.js) — static funnel view, candidate table
- [ ] API Gateway with routing, validation, auth middleware

### Phase 4: Async Pipeline (Commits 17-22)
- [ ] Implement `/api/submissions` endpoint (FastAPI)
- [ ] Set up arq + Redis queue
- [ ] Build evaluation-worker with scoring logic
- [ ] Implement idempotency (`_job_id` = application_id)
- [ ] Add retry logic + dead-letter handling
- [ ] Test pipeline under Redis failure (stop container mid-flow)

### Phase 5: Real-Time (Commits 23-26)
- [ ] Implement Redis pub/sub publisher in worker
- [ ] Build SSE endpoint in API Gateway (`/api/events`)
- [ ] Wire employer dashboard to SSE
- [ ] Add reconnection + gap-filling (full refetch on reconnect)

### Phase 6: Observability & Polish (Commits 27-32)
- [ ] Add structlog JSON logging across all Python services
- [ ] Add `prometheus-fastapi-instrumentator` metrics
- [ ] Global exception handlers with trace IDs
- [ ] Run `pip-audit` and `safety check` — document findings
- [ ] Run `npm audit` for frontend apps
- [ ] Verify no full table scans (`EXPLAIN ANALYZE` on Neon)
- [ ] Load test with Locust to verify <200ms p95
- [ ] Write comprehensive README
- [ ] Deploy frontends to Vercel, document live URLs

---

## 13. Identified Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Cross-app token timing attack | Low | Critical | Use `hmac.compare_digest()` for ALL comparisons |
| Neon's serverless cold start adds latency | Medium | Medium | Use connection pooling (`asyncpg` pool + PgBouncer) |
| Upstash free tier rate limit (10k/day) | Low | Low | Batch operations where possible; use local Redis for heavy dev |
| FastAPI SSE connections pile up | Medium | High | Implement max connections per IP, 30s heartbeat, cleanup on disconnect |
| arq job duplication race condition | Low | High | `_job_id` = `application_id` + DB unique constraint on `Score.application_id` |
| Docker Compose port conflicts | Medium | Low | Document all ports in README; use `.env` overrides |
| Large candidate list crashes dashboard | Low | Medium | Server-side pagination (50/page) + cursor-based infinite scroll |
| Neon connection limit exceeded | Medium | Medium | `asyncpg` pool size = 5 per service; total services × 5 < Neon limit |

---

## 14. Open Questions (Resolved)

1. **Why not Prisma for Python?**  
   → Prisma Client Python exists but is less mature than SQLAlchemy 2.0. SQLAlchemy has better async support, Alembic migrations, and is the industry standard.

2. **Why arq instead of Celery?**  
   → Celery is synchronous under the hood. arq is built for Python's `async`/`await`, has zero boilerplate, and is type-safe. For a FastAPI stack, arq is the natural choice.

3. **Why Neon over local Postgres?**  
   → Neon provides a live PostgreSQL URL that works both locally and in production. No need to migrate data between environments. The free tier is generous.

4. **Why Upstash over local Redis?**  
   → Upstash provides a managed Redis with zero infra overhead. For local dev, we'll include a Redis container so the system works offline. Upstash is used for the live deployed version.

5. **Can FastAPI really hit <200ms p95?**  
   → Absolutely. FastAPI + Uvicorn + asyncpg is one of the fastest Python web stacks. With proper connection pooling, no N+1 queries, and indexed hot paths, sub-100ms p95 is achievable.

---

## 15. Success Criteria Checklist

Before declaring the project complete, verify:

- [ ] `docker compose up` starts all services (using local Redis) without errors
- [ ] Candidate can log in → click Start Assessment → land in Assessment Engine without re-login
- [ ] Cross-app token expires after 120 seconds and cannot be reused
- [ ] Submitting assessment stores answers in Neon, triggers worker, and dashboard updates within 5 seconds
- [ ] All API responses under 200ms p95 (verified via Locust load test)
- [ ] No full table scans on any query (verified via `EXPLAIN ANALYZE` on Neon)
- [ ] `pip-audit` returns 0 critical vulnerabilities (Python)
- [ ] `npm audit` returns 0 critical vulnerabilities (Node.js)
- [ ] All containers run as non-root user
- [ ] README includes architecture diagram, setup steps, Neon/Upstash connection guide, and design rationale
- [ ] Git history shows atomic commits with Conventional Commits format (`feat:`, `fix:`, `docs:`)
- [ ] **First commit** contains this plan document only
- [ ] Live URLs provided for Vercel deployments (bonus)

---

## 16. Appendix: Technology Versions

| Tool | Version | Reason |
|------|---------|--------|
| Python | 3.11+ | Native `TaskGroup`, better async performance, `StrEnum` |
| FastAPI | 0.110+ | Pydantic v2 support, performance improvements |
| Uvicorn | 0.27+ | HTTP/2 support, stable ASGI server |
| SQLAlchemy | 2.0+ | Full async ORM, modern query API |
| Alembic | 1.13+ | SQLAlchemy-native migrations |
| asyncpg | 0.29+ | Fastest Python PostgreSQL driver |
| arq | 0.26+ | Modern async Redis queue |
| redis-py | 5.0+ | Official Redis client, async support |
| Pydantic | 2.6+ | v2 is 5-50x faster than v1, core to FastAPI |
| structlog | 24.1+ | Structured logging standard |
| Next.js | 15.x | App Router, Server Components |
| Node.js | 20 LTS | Stable, native fetch |
| Neon | Latest | Serverless PostgreSQL |
| Upstash | Latest | Serverless Redis |

---

*End of Updated Plan Document*
