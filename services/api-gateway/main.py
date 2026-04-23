import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, List, AsyncGenerator

import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import select, func, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator

from shared.database import get_db, AsyncSessionLocal
from shared.models import (
    User, UserRole, Application, ApplicationStatus,
    MCQQuestion, Response, Score, PendingEvaluation
)
from config import settings

app = FastAPI(title="Zetheta API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Redis client
redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


# ─── Pydantic Models ───

class AnswerSubmission(BaseModel):
    question_id: str
    selected_option: int


class SubmissionRequest(BaseModel):
    application_id: str
    answers: List[AnswerSubmission]


class SubmissionResponse(BaseModel):
    status: str
    application_id: str
    message: str


class QuestionOut(BaseModel):
    id: str
    question_text: str
    options: List[str]
    difficulty: int


class CandidateOut(BaseModel):
    id: str
    name: str
    email: str
    status: str
    application_status: Optional[str] = None
    score_percentage: Optional[float] = None


class ScoreOut(BaseModel):
    id: str
    application_id: str
    candidate_name: str
    percentage: float
    correct_count: int
    total_questions: int
    evaluated_at: datetime


class FunnelOut(BaseModel):
    applied: int
    attempted: int
    submitted: int
    evaluated: int


# ─── Auth Helpers ───

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        token_type = payload.get("type", "access")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user.token_type = token_type
    return user


async def require_employer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.EMPLOYER:
        raise HTTPException(status_code=403, detail="Employer access required")
    return current_user


async def get_assessment_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing session token")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "assessment_session":
            raise HTTPException(status_code=401, detail="Invalid session token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")


# ─── Endpoints ───

@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.get("/api/questions", response_model=List[QuestionOut])
async def get_questions(session: dict = Depends(get_assessment_session), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MCQQuestion).order_by(MCQQuestion.difficulty))
    questions = result.scalars().all()
    return [
        QuestionOut(
            id=str(q.id),
            question_text=q.question_text,
            options=q.options,
            difficulty=q.difficulty
        )
        for q in questions
    ]


@app.post("/api/submissions", response_model=SubmissionResponse)
async def submit_assessment(
    req: SubmissionRequest,
    session: dict = Depends(get_assessment_session),
    db: AsyncSession = Depends(get_db)
):
    application_id = uuid.UUID(req.application_id)
    session_app_id = uuid.UUID(session.get("application_id"))

    if application_id != session_app_id:
        raise HTTPException(status_code=403, detail="Session does not match application")

    # Verify application exists and belongs to candidate
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check if already submitted
    if application.status == ApplicationStatus.SUBMITTED:
        return SubmissionResponse(
            status="already_submitted",
            application_id=str(application_id),
            message="Assessment already submitted"
        )

    # Fetch questions to validate answers
    result = await db.execute(select(MCQQuestion))
    questions = {str(q.id): q for q in result.scalars().all()}

    # Store responses
    for ans in req.answers:
        question = questions.get(ans.question_id)
        if not question:
            continue
        is_correct = ans.selected_option == question.correct_option
        response = Response(
            id=uuid.uuid4(),
            application_id=application_id,
            question_id=uuid.UUID(ans.question_id),
            selected_option=ans.selected_option,
            is_correct=is_correct
        )
        db.add(response)

    application.status = ApplicationStatus.SUBMITTED
    application.submitted_at = datetime.utcnow()
    await db.commit()

    # Enqueue evaluation job
    try:
        # Use Redis to enqueue via a simple queue message for the worker
        job_payload = json.dumps({
            "application_id": str(application_id),
            "enqueued_at": datetime.utcnow().isoformat()
        })
        await redis_client.lpush("evaluation:queue", job_payload)
    except Exception:
        # Fallback: store in pending_evaluations for recovery
        pending = PendingEvaluation(
            id=uuid.uuid4(),
            application_id=application_id,
            queued_at=datetime.utcnow()
        )
        db.add(pending)
        await db.commit()

    return SubmissionResponse(
        status="submitted",
        application_id=str(application_id),
        message="Assessment submitted successfully. Evaluation in progress."
    )


@app.get("/api/candidates", response_model=List[CandidateOut])
async def list_candidates(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import or_

    query = select(User).where(User.role == UserRole.CANDIDATE)

    if status:
        query = query.where(User.status == status)

    if search:
        query = query.where(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()

    # Fetch latest application + score for each candidate
    candidates = []
    for u in users:
        app_result = await db.execute(
            select(Application).where(Application.candidate_id == u.id).order_by(Application.created_at.desc())
        )
        latest_app = app_result.scalars().first()

        score_pct = None
        app_status = None
        if latest_app:
            app_status = latest_app.status.value
            if latest_app.score:
                score_pct = latest_app.score.percentage

        candidates.append(CandidateOut(
            id=str(u.id),
            name=u.name,
            email=u.email,
            status=u.status.value,
            application_status=app_status,
            score_percentage=score_pct
        ))

    return candidates


@app.get("/api/scores", response_model=List[ScoreOut])
async def list_scores(
    min_score: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    query = select(Score, User).join(Application).join(User)

    if min_score is not None:
        query = query.where(Score.percentage >= min_score)

    query = query.order_by(Score.evaluated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    return [
        ScoreOut(
            id=str(score.id),
            application_id=str(score.application_id),
            candidate_name=user.name,
            percentage=score.percentage,
            correct_count=score.correct_count,
            total_questions=score.total_questions,
            evaluated_at=score.evaluated_at
        )
        for score, user in rows
    ]


@app.get("/api/analytics/funnel", response_model=FunnelOut)
async def get_funnel(current_user: User = Depends(require_employer), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application.status, func.count(Application.id)).group_by(Application.status)
    )
    counts = {status.value: count for status, count in result.all()}

    return FunnelOut(
        applied=counts.get("applied", 0) + counts.get("attempted", 0) + counts.get("submitted", 0) + counts.get("evaluated", 0),
        attempted=counts.get("attempted", 0) + counts.get("submitted", 0) + counts.get("evaluated", 0),
        submitted=counts.get("submitted", 0) + counts.get("evaluated", 0),
        evaluated=counts.get("evaluated", 0)
    )


@app.get("/api/events")
async def events_stream(token: Optional[str] = Query(None)):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("role") != "employer":
            raise HTTPException(status_code=403, detail="Employer access required")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def event_generator() -> AsyncGenerator[str, None]:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("scores")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe("scores")
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/submissions/{application_id}")
async def get_submission_status(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Application).where(Application.id == uuid.UUID(application_id))
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify ownership (candidate can only see their own)
    if current_user.role == UserRole.CANDIDATE and application.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    score_data = None
    if application.score:
        score_data = {
            "percentage": application.score.percentage,
            "correct_count": application.score.correct_count,
            "total_questions": application.score.total_questions,
            "evaluated_at": application.score.evaluated_at.isoformat()
        }

    return {
        "application_id": application_id,
        "status": application.status.value,
        "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
        "score": score_data
    }
