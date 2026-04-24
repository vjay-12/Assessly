import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    ForeignKey, Index, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ── Enums ──────────────────────────────────────────────

class UserRole(str, enum.Enum):
    CANDIDATE = "candidate"
    ADMIN = "admin"

class DifficultyLevel(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class EnrollmentStatus(str, enum.Enum):
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    IN_REVIEW = "In Review"

class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    ATTEMPTED = "attempted"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"

class SeverityLevel(str, enum.Enum):
    INFORMATIONAL = "Informational"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class AuditEventType(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ASSESSMENT_STARTED = "ASSESSMENT_STARTED"
    ASSESSMENT_SUBMITTED = "ASSESSMENT_SUBMITTED"
    ANSWER_SAVED = "ANSWER_SAVED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    TOKEN_ISSUED = "TOKEN_ISSUED"
    TOKEN_USED = "TOKEN_USED"
    TOKEN_INVALIDATED = "TOKEN_INVALIDATED"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    RESULT_OVERRIDE = "RESULT_OVERRIDE"
    PAGE_VISITED = "PAGE_VISITED"


# ── Users ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, native_enum=False), default=UserRole.CANDIDATE, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = relationship("AssessmentAssignment", back_populates="candidate")
    test_sessions = relationship("TestSession", back_populates="candidate")
    otp_tokens = relationship("OTPToken", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_role_created", "role", "created_at"),
    )


# ── Assessments ────────────────────────────────────────

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    difficulty = Column(Enum(DifficultyLevel, native_enum=False), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    total_questions = Column(Integer, default=0)
    pass_mark = Column(Integer, default=50, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    max_attempts = Column(Integer, default=1, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = relationship("Question", back_populates="assessment", cascade="all, delete-orphan")
    assignments = relationship("AssessmentAssignment", back_populates="assessment")
    test_sessions = relationship("TestSession", back_populates="assessment")


# ── Assessment Assignments ─────────────────────────────

class AssessmentAssignment(Base):
    __tablename__ = "assessment_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    assessment = relationship("Assessment", back_populates="assignments")
    candidate = relationship("User", back_populates="assignments")

    __table_args__ = (
        Index("ix_assignments_candidate", "candidate_id"),
        Index("ix_assignments_assessment", "assessment_id"),
        Index("ix_assignments_candidate_assessment", "candidate_id", "assessment_id", unique=True),
    )


# ── Questions ──────────────────────────────────────────

class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    code_snippet = Column(Text, nullable=True)
    options = Column(ARRAY(Text), nullable=False)
    correct_option = Column(Integer, nullable=False)
    points = Column(Integer, default=1, nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)
    sort_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    assessment = relationship("Assessment", back_populates="questions")
    responses = relationship("SessionResponse", back_populates="question")

    __table_args__ = (
        Index("ix_questions_assessment", "assessment_id"),
        Index("ix_questions_difficulty", "difficulty"),
    )


# ── Test Sessions ──────────────────────────────────────

class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(EnrollmentStatus, native_enum=False), default=EnrollmentStatus.ASSIGNED, nullable=False)
    application_status = Column(Enum(ApplicationStatus, native_enum=False), default=ApplicationStatus.APPLIED, nullable=False)
    score_percentage = Column(Float, nullable=True)
    total_questions = Column(Integer, nullable=True)
    correct_count = Column(Integer, nullable=True)
    total_answered = Column(Integer, default=0)
    time_taken_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String(100), nullable=True)
    proctor_log_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    candidate = relationship("User", back_populates="test_sessions")
    assessment = relationship("Assessment", back_populates="test_sessions")
    responses = relationship("SessionResponse", back_populates="session", cascade="all, delete-orphan")
    otp_tokens = relationship("OTPToken", back_populates="session")
    pending_evaluation = relationship("PendingEvaluation", back_populates="session", uselist=False)

    __table_args__ = (
        Index("ix_sessions_candidate", "candidate_id"),
        Index("ix_sessions_assessment", "assessment_id"),
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_app_status", "application_status"),
        Index("ix_sessions_evaluated", "evaluated_at"),
        Index("ix_sessions_submitted", "submitted_at"),
    )


# ── Session Responses ──────────────────────────────────

class SessionResponse(Base):
    __tablename__ = "session_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    selected_option = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    flagged = Column(Boolean, default=False, nullable=False)
    time_spent_seconds = Column(Integer, nullable=True)
    answered_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("TestSession", back_populates="responses")
    question = relationship("Question", back_populates="responses")

    __table_args__ = (
        Index("ix_responses_session", "session_id"),
        Index("ix_responses_question", "question_id"),
        Index("ix_responses_session_question", "session_id", "question_id", unique=True),
    )


# ── OTP Tokens ─────────────────────────────────────────

class OTPToken(Base):
    __tablename__ = "otp_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("test_sessions.id"), nullable=True)
    token_hash = Column(String(255), unique=True, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", back_populates="otp_tokens")
    session = relationship("TestSession", back_populates="otp_tokens")

    __table_args__ = (
        Index("ix_otp_token_hash", "token_hash"),
        Index("ix_otp_user_used", "user_id", "is_used"),
        Index("ix_otp_expires", "expires_at"),
    )


# ── Refresh Tokens ─────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_token_hash", "token_hash"),
        Index("ix_refresh_user", "user_id", "is_revoked"),
        Index("ix_refresh_expires", "expires_at"),
    )


# ── Pending Evaluations ────────────────────────────────

class PendingEvaluation(Base):
    __tablename__ = "pending_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("test_sessions.id"), nullable=False, index=True)
    queued_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    session = relationship("TestSession", back_populates="pending_evaluation")

    __table_args__ = (
        Index("ix_pending_session", "session_id"),
        Index("ix_pending_queued", "queued_at"),
    )


# ── Audit Logs ─────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    event_type = Column(Enum(AuditEventType, native_enum=False), nullable=False)
    severity = Column(Enum(SeverityLevel, native_enum=False), default=SeverityLevel.INFORMATIONAL, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_event_type", "event_type"),
        Index("ix_audit_severity", "severity"),
        Index("ix_audit_created", "created_at"),
    )


# ── Department Benchmarks ──────────────────────────────

class DepartmentBenchmark(Base):
    __tablename__ = "department_benchmarks"

    category = Column(String(100), primary_key=True)
    avg_score = Column(Float, nullable=True)
    candidate_count = Column(Integer, default=0)
    pass_rate = Column(Float, nullable=True)
    top_skills = Column(ARRAY(Text), nullable=True)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
