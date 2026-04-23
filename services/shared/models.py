import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, ForeignKey, Index, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserRole(str, enum.Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"


class CandidateStatus(str, enum.Enum):
    APPLIED = "applied"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    ATTEMPTED = "attempted"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CANDIDATE, nullable=False)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.APPLIED, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    applications = relationship("Application", back_populates="candidate")

    __table_args__ = (Index("ix_users_status_created", "status", "created_at"),)


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.APPLIED, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("User", back_populates="applications")
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
    question_text = Column(Text, nullable=False)
    options = Column(ARRAY(Text), nullable=False)
    correct_option = Column(Integer, nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    responses = relationship("Response", back_populates="question")

    __table_args__ = (Index("ix_questions_difficulty", "difficulty"),)


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


class PendingEvaluation(Base):
    __tablename__ = "pending_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    queued_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_pending_eval_app", "application_id"),)
