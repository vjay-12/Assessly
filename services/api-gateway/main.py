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
    User, UserRole, TestSession, ApplicationStatus,
    Question, SessionResponse, PendingEvaluation,
    Assessment, AssessmentAssignment, EnrollmentStatus
)
from shared.email import send_assignment_invite
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
    full_name: str
    email: str
    is_verified: bool
    application_status: Optional[str] = None
    score_percentage: Optional[float] = None


class ScoreOut(BaseModel):
    id: str
    application_id: str
    candidate_name: str
    percentage: float
    correct_count: int
    total_questions: int
    evaluated_at: Optional[datetime]


class FunnelOut(BaseModel):
    applied: int
    attempted: int
    submitted: int
    evaluated: int


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "candidate"


class CreateUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class AssignmentRequest(BaseModel):
    candidate_id: str
    assessment_id: str


class AssignmentResponse(BaseModel):
    id: str
    candidate_id: str
    assessment_id: str
    status: str
    assigned_at: datetime


class AssessmentOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    duration_minutes: int
    total_questions: int
    pass_mark: float
    is_published: bool


class MySessionOut(BaseModel):
    id: str
    assessment_title: str
    application_status: str
    score_percentage: Optional[float]
    assigned_at: Optional[datetime]


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
    if current_user.role != UserRole.ADMIN:
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
    result = await db.execute(select(Question).order_by(Question.difficulty))
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

    # Verify test session exists and belongs to candidate
    result = await db.execute(
        select(TestSession).where(TestSession.id == application_id)
    )
    test_session = result.scalar_one_or_none()
    if not test_session:
        raise HTTPException(status_code=404, detail="Test session not found")

    # Check if already submitted
    if test_session.application_status == ApplicationStatus.SUBMITTED:
        return SubmissionResponse(
            status="already_submitted",
            application_id=str(application_id),
            message="Assessment already submitted"
        )

    # Fetch questions to validate answers
    result = await db.execute(select(Question))
    questions = {str(q.id): q for q in result.scalars().all()}

    # Store responses
    for ans in req.answers:
        question = questions.get(ans.question_id)
        if not question:
            continue
        is_correct = ans.selected_option == question.correct_option
        response = SessionResponse(
            id=uuid.uuid4(),
            session_id=application_id,
            question_id=uuid.UUID(ans.question_id),
            selected_option=ans.selected_option,
            is_correct=is_correct
        )
        db.add(response)

    test_session.application_status = ApplicationStatus.SUBMITTED
    test_session.submitted_at = datetime.utcnow()
    await db.commit()

    # Enqueue evaluation job
    try:
        job_payload = json.dumps({
            "application_id": str(application_id),
            "enqueued_at": datetime.utcnow().isoformat()
        })
        await redis_client.lpush("evaluation:queue", job_payload)
    except Exception:
        # Fallback: store in pending_evaluations for recovery
        pending = PendingEvaluation(
            id=uuid.uuid4(),
            session_id=application_id,
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

    query = select(User).where(User.role == UserRole.CANDIDATE, User.is_deleted == False)

    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()

    # Fetch latest test session for each candidate
    candidates = []
    for u in users:
        app_result = await db.execute(
            select(TestSession).where(TestSession.candidate_id == u.id).order_by(TestSession.created_at.desc())
        )
        latest_app = app_result.scalars().first()

        score_pct = None
        app_status = None
        if latest_app:
            app_status = latest_app.application_status.value
            score_pct = latest_app.score_percentage

        candidates.append(CandidateOut(
            id=str(u.id),
            full_name=u.full_name,
            email=u.email,
            is_verified=u.is_verified,
            application_status=app_status,
            score_percentage=score_pct
        ))

    return candidates


@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_deleted = True
    await db.commit()
    return {"detail": "User deleted successfully"}


@app.get("/api/scores", response_model=List[ScoreOut])
async def list_scores(
    min_score: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(TestSession, User)
        .join(User, TestSession.candidate_id == User.id)
        .where(TestSession.application_status == ApplicationStatus.EVALUATED)
    )

    if min_score is not None:
        query = query.where(TestSession.score_percentage >= min_score)

    query = query.order_by(TestSession.evaluated_at.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    return [
        ScoreOut(
            id=str(ts.id),
            application_id=str(ts.id),
            candidate_name=user.full_name,
            percentage=ts.score_percentage or 0,
            correct_count=ts.correct_count or 0,
            total_questions=ts.total_questions or 0,
            evaluated_at=ts.evaluated_at
        )
        for ts, user in rows
    ]


@app.get("/api/analytics/funnel", response_model=FunnelOut)
async def get_funnel(current_user: User = Depends(require_employer), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestSession.application_status, func.count(TestSession.id)).group_by(TestSession.application_status)
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
        if payload.get("role") != "admin":
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
        select(TestSession).where(TestSession.id == uuid.UUID(application_id))
    )
    test_session = result.scalar_one_or_none()
    if not test_session:
        raise HTTPException(status_code=404, detail="Test session not found")

    # Verify ownership (candidate can only see their own)
    if current_user.role == UserRole.CANDIDATE and test_session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    score_data = None
    if test_session.application_status == ApplicationStatus.EVALUATED:
        score_data = {
            "percentage": test_session.score_percentage,
            "correct_count": test_session.correct_count,
            "total_questions": test_session.total_questions,
            "evaluated_at": test_session.evaluated_at.isoformat() if test_session.evaluated_at else None
        }

    return {
        "application_id": application_id,
        "status": test_session.application_status.value,
        "submitted_at": test_session.submitted_at.isoformat() if test_session.submitted_at else None,
        "score": score_data
    }


@app.post("/api/users", response_model=CreateUserResponse)
async def create_user(
    req: CreateUserRequest,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    import bcrypt
    role = UserRole.ADMIN if req.role.lower() == "admin" else UserRole.CANDIDATE
    password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()

    result = await db.execute(select(User).where(User.email == req.email))
    existing = result.scalar_one_or_none()

    if existing:
        if existing.is_deleted:
            # Restore soft-deleted user
            existing.is_deleted = False
            existing.full_name = req.full_name
            existing.password_hash = password_hash
            existing.role = role
            existing.is_verified = True
            await db.commit()

            import asyncio
            asyncio.create_task(asyncio.to_thread(send_welcome_email, existing.email, existing.full_name, req.password))

            return CreateUserResponse(
                id=str(existing.id),
                email=existing.email,
                full_name=existing.full_name,
                role=existing.role.value,
            )
        else:
            raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        full_name=req.full_name,
        password_hash=password_hash,
        role=role,
        is_verified=True,
    )
    db.add(user)
    await db.commit()

    # Send welcome email asynchronously
    import asyncio
    asyncio.create_task(asyncio.to_thread(send_welcome_email, user.email, user.full_name, req.password))

    return CreateUserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
    )


@app.get("/api/assessments", response_model=List[AssessmentOut])
async def list_assessments(
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assessment).where(Assessment.is_published == True))
    assessments = result.scalars().all()
    return [
        AssessmentOut(
            id=str(a.id),
            title=a.title,
            description=a.description,
            category=a.category,
            difficulty=a.difficulty.value if hasattr(a.difficulty, 'value') else str(a.difficulty),
            duration_minutes=a.duration_minutes,
            total_questions=a.total_questions,
            pass_mark=a.pass_mark,
            is_published=a.is_published,
        )
        for a in assessments
    ]


@app.post("/api/assignments", response_model=AssignmentResponse)
async def create_assignment(
    req: AssignmentRequest,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    # Validate candidate
    result = await db.execute(select(User).where(User.id == uuid.UUID(req.candidate_id)))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if candidate.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=400, detail="Target user is not a candidate")

    # Validate assessment
    result = await db.execute(select(Assessment).where(Assessment.id == uuid.UUID(req.assessment_id)))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Create assignment
    assignment = AssessmentAssignment(
        id=uuid.uuid4(),
        candidate_id=uuid.UUID(req.candidate_id),
        assessment_id=uuid.UUID(req.assessment_id),
    )
    db.add(assignment)

    # Create test session
    test_session = TestSession(
        id=uuid.uuid4(),
        candidate_id=uuid.UUID(req.candidate_id),
        assessment_id=uuid.UUID(req.assessment_id),
        application_status=ApplicationStatus.APPLIED,
    )
    db.add(test_session)
    await db.commit()

    # Send assignment invite email asynchronously
    import asyncio
    asyncio.create_task(asyncio.to_thread(send_assignment_invite, candidate.email, candidate.full_name, assessment.title))

    return AssignmentResponse(
        id=str(assignment.id),
        candidate_id=str(assignment.candidate_id),
        assessment_id=str(assignment.assessment_id),
        status="assigned",
        assigned_at=assignment.assigned_at if assignment.assigned_at else datetime.utcnow(),
    )


@app.get("/api/assignments", response_model=List[AssignmentResponse])
async def list_assignments(
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AssessmentAssignment))
    assignments = result.scalars().all()
    return [
        AssignmentResponse(
            id=str(a.id),
            candidate_id=str(a.candidate_id),
            assessment_id=str(a.assessment_id),
            status="assigned",
            assigned_at=a.assigned_at if a.assigned_at else datetime.utcnow(),
        )
        for a in assignments
    ]


@app.get("/api/my-sessions", response_model=List[MySessionOut])
async def get_my_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return the current candidate's test sessions with assessment details."""
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=403, detail="Candidate access only")

    result = await db.execute(
        select(TestSession, Assessment)
        .join(Assessment, TestSession.assessment_id == Assessment.id)
        .where(TestSession.candidate_id == current_user.id)
        .order_by(TestSession.created_at.desc())
    )
    rows = result.all()

    return [
        MySessionOut(
            id=str(session.id),
            assessment_title=assessment.title,
            application_status=session.application_status.value,
            score_percentage=session.score_percentage,
            assigned_at=session.created_at,
        )
        for session, assessment in rows
    ]


# ─── Assessment Builder Endpoints ───

class QuestionIn(BaseModel):
    id: Optional[str] = None
    question_text: str
    code_snippet: Optional[str] = ""
    options: List[str]
    correct_option: int
    points: int = 1
    difficulty: int = 1
    sort_order: int = 0


class AssessmentIn(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str
    difficulty: str
    duration_minutes: int
    pass_mark: int
    max_attempts: int = 1
    is_published: bool = False
    questions: List[QuestionIn]


class QuestionOut(BaseModel):
    id: str
    question_text: str
    code_snippet: Optional[str]
    options: List[str]
    correct_option: int
    points: int
    difficulty: int
    sort_order: int


class AssessmentDetailOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    duration_minutes: int
    total_questions: int
    pass_mark: int
    max_attempts: int
    is_published: bool
    created_at: datetime
    questions: List[QuestionOut]


class ManageAssessmentOut(BaseModel):
    id: str
    title: str
    category: str
    difficulty: str
    duration_minutes: int
    pass_mark: int
    is_published: bool
    total_questions: int
    created_at: datetime


class BulkAssignRequest(BaseModel):
    candidate_ids: List[str]
    due_at: Optional[str] = None


class CandidateForAssignmentOut(BaseModel):
    id: str
    full_name: str
    email: str
    already_assigned: bool


@app.post("/api/assessments", response_model=ManageAssessmentOut)
async def create_assessment(
    req: AssessmentIn,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    if req.is_published and not req.questions:
        raise HTTPException(status_code=400, detail="At least one question is required before publishing")

    assessment = Assessment(
        id=uuid.uuid4(),
        title=req.title,
        description=req.description or "",
        category=req.category,
        difficulty=DifficultyLevel[req.difficulty.upper()],
        duration_minutes=req.duration_minutes,
        total_questions=len(req.questions),
        pass_mark=req.pass_mark,
        max_attempts=req.max_attempts,
        is_published=req.is_published,
        created_by=current_user.id,
    )
    db.add(assessment)
    await db.flush()

    for q in req.questions:
        db.add(Question(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            question_text=q.question_text,
            code_snippet=q.code_snippet or None,
            options=q.options,
            correct_option=q.correct_option,
            points=q.points,
            difficulty=q.difficulty,
            sort_order=q.sort_order,
        ))

    await db.commit()

    # Defensive: SQLAlchemy may return enum or string depending on state
    diff_val = assessment.difficulty.value if hasattr(assessment.difficulty, 'value') else assessment.difficulty

    return ManageAssessmentOut(
        id=str(assessment.id),
        title=assessment.title,
        category=assessment.category,
        difficulty=diff_val,
        duration_minutes=assessment.duration_minutes,
        pass_mark=assessment.pass_mark,
        is_published=assessment.is_published,
        total_questions=assessment.total_questions,
        created_at=assessment.created_at,
    )


@app.get("/api/assessments/{assessment_id}", response_model=AssessmentDetailOut)
async def get_assessment_detail(
    assessment_id: str,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assessment).where(Assessment.id == uuid.UUID(assessment_id)))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    q_result = await db.execute(
        select(Question).where(Question.assessment_id == assessment.id).order_by(Question.sort_order)
    )
    questions = q_result.scalars().all()

    diff_val = assessment.difficulty.value if hasattr(assessment.difficulty, 'value') else assessment.difficulty

    return AssessmentDetailOut(
        id=str(assessment.id),
        title=assessment.title,
        description=assessment.description or "",
        category=assessment.category,
        difficulty=diff_val,
        duration_minutes=assessment.duration_minutes,
        total_questions=assessment.total_questions,
        pass_mark=assessment.pass_mark,
        max_attempts=assessment.max_attempts,
        is_published=assessment.is_published,
        created_at=assessment.created_at,
        questions=[
            QuestionOut(
                id=str(q.id),
                question_text=q.question_text,
                code_snippet=q.code_snippet,
                options=q.options,
                correct_option=q.correct_option,
                points=q.points,
                difficulty=q.difficulty,
                sort_order=q.sort_order or 0,
            )
            for q in questions
        ],
    )


@app.put("/api/assessments/{assessment_id}", response_model=ManageAssessmentOut)
async def update_assessment(
    assessment_id: str,
    req: AssessmentIn,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assessment).where(Assessment.id == uuid.UUID(assessment_id)))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    assessment.title = req.title
    assessment.description = req.description or ""
    assessment.category = req.category
    assessment.difficulty = DifficultyLevel[req.difficulty.upper()]
    assessment.duration_minutes = req.duration_minutes
    assessment.pass_mark = req.pass_mark
    assessment.max_attempts = req.max_attempts
    assessment.is_published = req.is_published
    assessment.total_questions = len(req.questions)

    # Delete existing questions and recreate
    await db.execute(
        Question.__table__.delete().where(Question.assessment_id == assessment.id)
    )

    for q in req.questions:
        db.add(Question(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            question_text=q.question_text,
            code_snippet=q.code_snippet or None,
            options=q.options,
            correct_option=q.correct_option,
            points=q.points,
            difficulty=q.difficulty,
            sort_order=q.sort_order,
        ))

    await db.commit()

    diff_val = assessment.difficulty.value if hasattr(assessment.difficulty, 'value') else assessment.difficulty

    return ManageAssessmentOut(
        id=str(assessment.id),
        title=assessment.title,
        category=assessment.category,
        difficulty=diff_val,
        duration_minutes=assessment.duration_minutes,
        pass_mark=assessment.pass_mark,
        is_published=assessment.is_published,
        total_questions=assessment.total_questions,
        created_at=assessment.created_at,
    )


@app.delete("/api/assessments/{assessment_id}")
async def delete_assessment(
    assessment_id: str,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assessment).where(Assessment.id == uuid.UUID(assessment_id)))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Check for active test sessions
    active_result = await db.execute(
        select(TestSession).where(
            TestSession.assessment_id == assessment.id,
            TestSession.application_status.in_([ApplicationStatus.ATTEMPTED, ApplicationStatus.SUBMITTED])
        )
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cannot delete assessment with active sessions")

    await db.delete(assessment)
    await db.commit()
    return {"message": "Assessment deleted"}


@app.post("/api/assessments/{assessment_id}/duplicate", response_model=ManageAssessmentOut)
async def duplicate_assessment(
    assessment_id: str,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assessment).where(Assessment.id == uuid.UUID(assessment_id)))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Copy assessment
    new_assessment = Assessment(
        id=uuid.uuid4(),
        title=f"{source.title} (Copy)",
        description=source.description,
        category=source.category,
        difficulty=source.difficulty,
        duration_minutes=source.duration_minutes,
        total_questions=source.total_questions,
        pass_mark=source.pass_mark,
        max_attempts=source.max_attempts,
        is_published=False,
        created_by=current_user.id,
    )
    db.add(new_assessment)
    await db.flush()

    # Copy questions
    q_result = await db.execute(select(Question).where(Question.assessment_id == source.id))
    for q in q_result.scalars().all():
        db.add(Question(
            id=uuid.uuid4(),
            assessment_id=new_assessment.id,
            question_text=q.question_text,
            code_snippet=q.code_snippet,
            options=q.options,
            correct_option=q.correct_option,
            points=q.points,
            difficulty=q.difficulty,
            sort_order=q.sort_order,
        ))

    await db.commit()

    diff_val = new_assessment.difficulty.value if hasattr(new_assessment.difficulty, 'value') else new_assessment.difficulty

    return ManageAssessmentOut(
        id=str(new_assessment.id),
        title=new_assessment.title,
        category=new_assessment.category,
        difficulty=diff_val,
        duration_minutes=new_assessment.duration_minutes,
        pass_mark=new_assessment.pass_mark,
        is_published=new_assessment.is_published,
        total_questions=new_assessment.total_questions,
        created_at=new_assessment.created_at,
    )


@app.get("/api/assessments-all", response_model=List[ManageAssessmentOut])
async def list_all_assessments(
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    query = select(Assessment)

    if category:
        query = query.where(Assessment.category == category)
    if difficulty:
        query = query.where(Assessment.difficulty == DifficultyLevel[difficulty.upper()])
    if status:
        is_pub = status.lower() == "published"
        query = query.where(Assessment.is_published == is_pub)
    if search:
        query = query.where(Assessment.title.ilike(f"%{search}%"))

    query = query.order_by(Assessment.created_at.desc())
    result = await db.execute(query)
    assessments = result.scalars().all()

    return [
        ManageAssessmentOut(
            id=str(a.id),
            title=a.title,
            category=a.category,
            difficulty=a.difficulty.value if hasattr(a.difficulty, 'value') else a.difficulty,
            duration_minutes=a.duration_minutes,
            pass_mark=a.pass_mark,
            is_published=a.is_published,
            total_questions=a.total_questions,
            created_at=a.created_at,
        )
        for a in assessments
    ]


@app.get("/api/candidates/for-assignment/{assessment_id}", response_model=List[CandidateForAssignmentOut])
async def get_candidates_for_assignment(
    assessment_id: str,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.role == UserRole.CANDIDATE))
    candidates = result.scalars().all()

    # Check existing assignments
    assign_result = await db.execute(
        select(AssessmentAssignment.candidate_id).where(
            AssessmentAssignment.assessment_id == uuid.UUID(assessment_id)
        )
    )
    assigned_ids = {str(row[0]) for row in assign_result.all()}

    return [
        CandidateForAssignmentOut(
            id=str(c.id),
            full_name=c.full_name,
            email=c.email,
            already_assigned=str(c.id) in assigned_ids,
        )
        for c in candidates
    ]


@app.post("/api/assessments/{assessment_id}/assign-bulk")
async def bulk_assign_assessment(
    assessment_id: str,
    req: BulkAssignRequest,
    current_user: User = Depends(require_employer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assessment).where(Assessment.id == uuid.UUID(assessment_id)))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    assigned_count = 0
    for candidate_id in req.candidate_ids:
        # Check if already assigned
        existing = await db.execute(
            select(AssessmentAssignment).where(
                AssessmentAssignment.assessment_id == assessment.id,
                AssessmentAssignment.candidate_id == uuid.UUID(candidate_id)
            )
        )
        if existing.scalar_one_or_none():
            continue

        assignment = AssessmentAssignment(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            candidate_id=uuid.UUID(candidate_id),
            due_at=datetime.fromisoformat(req.due_at) if req.due_at else None,
        )
        db.add(assignment)

        # Create test session
        test_session = TestSession(
            id=uuid.uuid4(),
            candidate_id=uuid.UUID(candidate_id),
            assessment_id=assessment.id,
            application_status=ApplicationStatus.APPLIED,
        )
        db.add(test_session)
        assigned_count += 1

        # Send email
        candidate_result = await db.execute(select(User).where(User.id == uuid.UUID(candidate_id)))
        candidate = candidate_result.scalar_one_or_none()
        if candidate:
            asyncio.create_task(asyncio.to_thread(send_assignment_invite, candidate.email, candidate.full_name, assessment.title))

    await db.commit()

    return {"message": f"Assigned to {assigned_count} candidate(s)", "assigned_count": assigned_count}
