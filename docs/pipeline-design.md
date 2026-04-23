# Pipeline Design — Async Evaluation

## Sequence

```
Assessment Engine          API Gateway              Valkey              Worker
     │                        │                      │                   │
     │ POST /api/submissions  │                      │                   │
     │───────────────────────>│                      │                   │
     │                        │ 1. INSERT responses  │                   │
     │                        │ 2. UPDATE status     │                   │
     │                        │ 3. LPUSH queue       │                   │
     │                        │─────────────────────>│                   │
     │                        │                      │                   │
     │  {status: "submitted"} │                      │                   │
     │<───────────────────────│                      │                   │
     │                        │                      │  BRPOP evaluation  │
     │                        │                      │<──────────────────│
     │                        │                      │                   │
     │                        │                      │                   │  PROCESS
     │                        │                      │                   │  • Check idempotency
     │                        │                      │                   │  • Compute score
     │                        │                      │                   │  • INSERT score
     │                        │                      │                   │  • PUBLISH event
     │                        │                      │                   │
     │                        │   Redis PUB/SUB      │                   │
     │                        │<─────────────────────────────────────────│
     │                        │                      │                   │
     │                        │   SSE /api/events    │                   │
     │                        │────────────────────────────────────────>│
     │                        │                      │                   │
```

## Idempotency

The `_job_id` equivalent is the `application_id` itself. Before scoring, the worker checks:

```python
existing = await db.execute(select(Score).where(Score.application_id == app_id))
if existing.scalar_one_or_none():
    return {"status": "already_evaluated"}
```

The database `UNIQUE` constraint on `Score.application_id` provides a hard guarantee against race conditions.

## Retry Strategy

| Error Type | Behavior |
|-----------|----------|
| Database timeout | Retry with exponential backoff (max 3) |
| Valkey pub/sub failure | Log warning; score is still committed |
| No responses found | Unrecoverable — dead letter after 3 retries |
| Score already exists | Return success (idempotent) |

## Fault Tolerance — Redis/Valkey Downtime

**Scenario: Valkey unavailable during submission**
1. API Gateway stores submission in Neon first (transaction)
2. Queue addition fails → return 202 "Evaluation pending"
3. Submission is stored in `pending_evaluations` table
4. Recovery cron (60s interval) scans for `SUBMITTED` apps without `Score`
5. Re-enqueues orphaned applications when Valkey recovers

**Guarantee: Zero data loss even with prolonged Valkey outage.**

## Worker Implementation

The worker is a long-running Python process using `redis.asyncio`:
- `BRPOP` blocks until a job arrives (1s timeout for periodic recovery checks)
- Processes job within async SQLAlchemy session
- Publishes completion event to `scores` channel
- Handles exceptions with retry counter tracking
