import os
import uuid
import json
import asyncio
import structlog
import logging
from datetime import datetime

import redis.asyncio as redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import DB, init_engine
from shared.models import Base, TestSession, ApplicationStatus, SessionResponse, Question, PendingEvaluation, User, Assessment, AuditLog, AuditEventType, AuditEventCategory, SeverityLevel
from shared.email import send_result_notification

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
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

logger = structlog.get_logger("evaluation-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://valkey:6379")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")


async def process_evaluation(application_id: str, db: AsyncSession, redis_client: redis.Redis) -> dict:
    app_uuid = uuid.UUID(application_id)

    # 1. Idempotency check
    result = await db.execute(
        select(TestSession).where(
            TestSession.id == app_uuid,
            TestSession.application_status == ApplicationStatus.EVALUATED
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("session_already_evaluated", application_id=application_id)
        return {"status": "already_evaluated", "session_id": str(existing.id)}

    # 2. Fetch the test session to get assessment_id
    session_result = await db.execute(select(TestSession).where(TestSession.id == app_uuid))
    test_session = session_result.scalar_one_or_none()
    if not test_session:
        raise Exception(f"Test session {application_id} not found")

    # 3. Fetch actual total questions for this assessment
    from shared.models import Assessment
    assess_result = await db.execute(
        select(Assessment).where(Assessment.id == test_session.assessment_id)
    )
    assessment = assess_result.scalar_one_or_none()
    total_questions = assessment.total_questions if assessment else 0

    # 4. Fetch responses with questions
    result = await db.execute(
        select(SessionResponse, Question)
        .join(Question, SessionResponse.question_id == Question.id)
        .where(SessionResponse.session_id == app_uuid)
    )
    rows = result.all()

    if not rows:
        logger.warning("no_responses_found", application_id=application_id)
        raise Exception(f"No responses found for session {application_id}")

    # 5. Compute score
    total_answered = len(rows)
    correct = 0
    for response, question in rows:
        response.is_correct = (response.selected_option == question.correct_option)
        if response.is_correct:
            correct += 1

    percentage = (correct / total_questions) * 100 if total_questions > 0 else 0

    # 6. Update test session with score and status
    await db.execute(
        update(TestSession)
        .where(TestSession.id == app_uuid)
        .values(
            application_status=ApplicationStatus.EVALUATED,
            score_percentage=percentage,
            total_questions=total_questions,
            correct_count=correct,
            total_answered=total_answered,
            evaluated_at=datetime.utcnow(),
            worker_id=WORKER_ID
        )
    )
    await db.commit()

    # 5. Log audit event
    db.add(AuditLog(
        user_id=test_session.candidate_id if test_session else None,
        event_type=AuditEventType.EVAL_COMPLETED,
        category=AuditEventCategory.EVALUATION,
        severity=SeverityLevel.INFORMATIONAL,
        assessment_id=test_session.assessment_id if test_session else None,
        details=f"Evaluation completed for session {application_id}. Score: {percentage:.1f}% ({correct}/{total_questions})",
    ))
    await db.commit()

    # 6. Publish real-time event
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
    pending_result = await db.execute(
        select(PendingEvaluation).where(PendingEvaluation.session_id == app_uuid)
    )
    pending = pending_result.scalar_one_or_none()
    if pending:
        await db.delete(pending)
        await db.commit()

    # 7. Send result notification email
    try:
        session_result = await db.execute(select(TestSession).where(TestSession.id == app_uuid))
        session = session_result.scalar_one_or_none()
        if session:
            user_result = await db.execute(select(User).where(User.id == session.candidate_id))
            user = user_result.scalar_one_or_none()
            assess_result = await db.execute(select(Assessment).where(Assessment.id == session.assessment_id))
            assess = assess_result.scalar_one_or_none()
            if user and assess:
                import asyncio
                asyncio.create_task(asyncio.to_thread(send_result_notification, user.email, user.full_name, assess.title, percentage))
    except Exception as e:
        logger.warning("email_notification_failed", error=str(e))

    logger.info(
        "evaluation_completed",
        application_id=application_id,
        percentage=percentage,
        correct=correct,
        total=total_questions,
        worker_id=WORKER_ID
    )

    return {"status": "completed", "session_id": str(app_uuid), "percentage": percentage}


async def recover_pending_evaluations(db: AsyncSession, redis_client: redis.Redis):
    """Scan for SUBMITTED test sessions without evaluation and re-enqueue them."""
    result = await db.execute(
        select(TestSession.id)
        .where(TestSession.application_status == ApplicationStatus.SUBMITTED)
        .where(TestSession.score_percentage.is_(None))
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

    await init_engine()
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)

    # Ensure tables exist
    async with DB.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Log worker started system event
    async with DB.AsyncSessionLocal() as db:
        db.add(AuditLog(
            event_type=AuditEventType.WORKER_STARTED,
            category=AuditEventCategory.SYSTEM,
            severity=SeverityLevel.INFORMATIONAL,
            details=f"Evaluation worker {WORKER_ID} started",
        ))
        await db.commit()

    recovery_counter = 0

    while True:
        try:
            # Periodic recovery scan every ~60 iterations (~60 seconds)
            recovery_counter += 1
            if recovery_counter >= 60:
                recovery_counter = 0
                async with DB.AsyncSessionLocal() as db:
                    await recover_pending_evaluations(db, redis_client)

            # Block and wait for job (timeout 1s to allow recovery checks)
            result = await redis_client.brpop("evaluation:queue", timeout=1)
            if not result:
                continue

            _, job_json = result
            job = json.loads(job_json)
            application_id = job["application_id"]

            logger.info("job_received", application_id=application_id)

            async with DB.AsyncSessionLocal() as db:
                try:
                    # Log evaluation started
                    db.add(AuditLog(
                        event_type=AuditEventType.EVAL_STARTED,
                        category=AuditEventCategory.EVALUATION,
                        severity=SeverityLevel.INFORMATIONAL,
                        details=f"Evaluation started for session {application_id}",
                    ))
                    await db.commit()
                    await process_evaluation(application_id, db, redis_client)
                except Exception as e:
                    logger.error(
                        "evaluation_failed",
                        application_id=application_id,
                        error=str(e)
                    )
                    # Log evaluation failed
                    db.add(AuditLog(
                        event_type=AuditEventType.EVAL_FAILED,
                        category=AuditEventCategory.EVALUATION,
                        severity=SeverityLevel.HIGH,
                        details=f"Evaluation failed for session {application_id}: {str(e)}",
                    ))
                    await db.commit()
                    # Re-queue for retry (max 3 attempts tracked via simple counter)
                    attempts = job.get("attempts", 0) + 1
                    if attempts < 3:
                        job["attempts"] = attempts
                        await redis_client.lpush("evaluation:queue", json.dumps(job))
                        logger.info("job_requeued", application_id=application_id, attempt=attempts)
                        db.add(AuditLog(
                            event_type=AuditEventType.EVAL_RETRY,
                            category=AuditEventCategory.EVALUATION,
                            severity=SeverityLevel.MEDIUM,
                            details=f"Evaluation requeued for session {application_id}, attempt {attempts}",
                        ))
                        await db.commit()
                    else:
                        logger.error("job_dead_letter", application_id=application_id)
                        db.add(AuditLog(
                            event_type=AuditEventType.EVAL_DEAD,
                            category=AuditEventCategory.EVALUATION,
                            severity=SeverityLevel.CRITICAL,
                            details=f"Evaluation permanently failed for session {application_id} after 3 attempts",
                        ))
                        await db.commit()

        except Exception as e:
            logger.error("worker_loop_error", error=str(e))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
