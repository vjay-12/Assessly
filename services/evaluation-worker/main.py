import os
import uuid
import json
import asyncio
import structlog
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import AsyncSessionLocal, engine
from shared.models import Base, Application, ApplicationStatus, Response, MCQQuestion, Score, PendingEvaluation

logger = structlog.get_logger("evaluation-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://valkey:6379")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")


async def process_evaluation(application_id: str, db: AsyncSession, redis_client: redis.Redis) -> dict:
    app_uuid = uuid.UUID(application_id)

    # 1. Idempotency check
    result = await db.execute(select(Score).where(Score.application_id == app_uuid))
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("score_already_exists", application_id=application_id)
        return {"status": "already_evaluated", "score_id": str(existing.id)}

    # 2. Fetch responses with questions
    result = await db.execute(
        select(Response, MCQQuestion)
        .join(MCQQuestion, Response.question_id == MCQQuestion.id)
        .where(Response.application_id == app_uuid)
    )
    rows = result.all()

    if not rows:
        logger.warning("no_responses_found", application_id=application_id)
        raise Exception(f"No responses found for application {application_id}")

    # 3. Compute score
    total = len(rows)
    correct = 0
    for response, question in rows:
        response.is_correct = (response.selected_option == question.correct_option)
        if response.is_correct:
            correct += 1

    percentage = (correct / total) * 100 if total > 0 else 0

    # 4. Store score + update application status
    score = Score(
        id=uuid.uuid4(),
        application_id=app_uuid,
        total_questions=total,
        correct_count=correct,
        percentage=percentage,
        worker_id=WORKER_ID,
    )

    await db.execute(
        update(Application)
        .where(Application.id == app_uuid)
        .values(status=ApplicationStatus.EVALUATED)
    )

    db.add(score)
    await db.commit()

    # 5. Publish real-time event
    event = json.dumps({
        "type": "EVALUATION_COMPLETED",
        "payload": {
            "application_id": application_id,
            "percentage": round(percentage, 2),
            "evaluated_at": datetime.utcnow().isoformat(),
            "worker_id": WORKER_ID
        }
    })
    await redis_client.publish("scores", event)

    # 6. Remove from pending_evaluations if exists
    await db.execute(
        select(PendingEvaluation).where(PendingEvaluation.application_id == app_uuid)
    )
    # Cleanup handled by cascade or manual delete
    pending_result = await db.execute(
        select(PendingEvaluation).where(PendingEvaluation.application_id == app_uuid)
    )
    pending = pending_result.scalar_one_or_none()
    if pending:
        await db.delete(pending)
        await db.commit()

    logger.info(
        "evaluation_completed",
        application_id=application_id,
        percentage=percentage,
        correct=correct,
        total=total,
        worker_id=WORKER_ID
    )

    return {"status": "completed", "score_id": str(score.id), "percentage": percentage}


async def recover_pending_evaluations(db: AsyncSession, redis_client: redis.Redis):
    """Scan for SUBMITTED applications without scores and re-enqueue them."""
    result = await db.execute(
        select(Application.id)
        .where(Application.status == ApplicationStatus.SUBMITTED)
        .where(~select(Score).where(Score.application_id == Application.id).exists())
    )
    orphaned = result.scalars().all()

    for app_id in orphaned:
        job_payload = json.dumps({
            "application_id": str(app_id),
            "enqueued_at": datetime.utcnow().isoformat(),
            "source": "recovery"
        })
        await redis_client.lpush("evaluation:queue", job_payload)
        logger.info("recovered_orphaned_evaluation", application_id=str(app_id))


async def main():
    logger.info("worker_started", worker_id=WORKER_ID)

    redis_client = redis.from_url(REDIS_URL, decode_responses=True)

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    recovery_counter = 0

    while True:
        try:
            # Periodic recovery scan every ~60 iterations (~60 seconds)
            recovery_counter += 1
            if recovery_counter >= 60:
                recovery_counter = 0
                async with AsyncSessionLocal() as db:
                    await recover_pending_evaluations(db, redis_client)

            # Block and wait for job (timeout 1s to allow recovery checks)
            result = await redis_client.brpop("evaluation:queue", timeout=1)
            if not result:
                continue

            _, job_json = result
            job = json.loads(job_json)
            application_id = job["application_id"]

            logger.info("job_received", application_id=application_id)

            async with AsyncSessionLocal() as db:
                try:
                    await process_evaluation(application_id, db, redis_client)
                except Exception as e:
                    logger.error(
                        "evaluation_failed",
                        application_id=application_id,
                        error=str(e)
                    )
                    # Re-queue for retry (max 3 attempts tracked via simple counter)
                    attempts = job.get("attempts", 0) + 1
                    if attempts < 3:
                        job["attempts"] = attempts
                        await redis_client.lpush("evaluation:queue", json.dumps(job))
                        logger.info("job_requeued", application_id=application_id, attempt=attempts)
                    else:
                        logger.error("job_dead_letter", application_id=application_id)

        except Exception as e:
            logger.error("worker_loop_error", error=str(e))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
