import asyncio
import os
import bcrypt
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import engine, AsyncSessionLocal
from models import (
    Base, User, UserRole, Assessment, DifficultyLevel,
    TestSession, ApplicationStatus, EnrollmentStatus,
    Question
)

load_dotenv()


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # ── Users ──
        async def get_or_create_user(email, full_name, password, role, is_verified=True):
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                print(f"  User {email} already exists, skipping.")
                return user
            user = User(
                id=uuid.uuid4(),
                email=email,
                full_name=full_name,
                password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                role=role,
                is_verified=is_verified,
            )
            session.add(user)
            await session.commit()
            print(f"  Created user {email}.")
            return user

        alex = await get_or_create_user(
            "alex.rivera@example.com", "Alex Rivera", "candidate123", UserRole.CANDIDATE
        )
        sarah = await get_or_create_user(
            "sarah.jenkins@example.com", "Sarah Jenkins", "candidate123", UserRole.CANDIDATE
        )
        michael = await get_or_create_user(
            "michael.chen@example.com", "Michael Chen", "candidate123", UserRole.CANDIDATE, is_verified=False
        )
        admin = await get_or_create_user(
            "hr@assessly.com", "HR Admin", "admin123", UserRole.ADMIN
        )

        # ── Assessment ──
        result = await session.execute(
            select(Assessment).where(Assessment.title == "Full Stack Engineering Assessment")
        )
        assessment = result.scalar_one_or_none()
        if not assessment:
            assessment = Assessment(
                id=uuid.uuid4(),
                title="Full Stack Engineering Assessment",
                description="A comprehensive assessment covering backend architecture, databases, and system design.",
                category="Engineering",
                difficulty=DifficultyLevel.MEDIUM,
                duration_minutes=60,
                total_questions=10,
                pass_mark=50,
                is_published=True,
                max_attempts=2,
                created_by=admin.id,
            )
            session.add(assessment)
            await session.commit()
            print("  Created assessment.")

            questions = [
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="What is the primary purpose of an API Gateway in a microservices architecture?",
                    options=[
                        "To store business logic",
                        "To route requests, enforce authentication, and aggregate responses",
                        "To replace the need for a database",
                        "To compile frontend assets"
                    ],
                    correct_option=1,
                    points=1,
                    difficulty=1,
                    sort_order=1,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="Which HTTP status code indicates a successful creation of a resource?",
                    options=["200 OK", "201 Created", "204 No Content", "400 Bad Request"],
                    correct_option=1,
                    points=1,
                    difficulty=1,
                    sort_order=2,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="In Python's asyncio, what does 'await' do?",
                    options=[
                        "Pauses the entire program",
                        "Yields control back to the event loop until the awaited coroutine completes",
                        "Creates a new thread",
                        "Blocks the main thread synchronously"
                    ],
                    correct_option=1,
                    points=2,
                    difficulty=2,
                    sort_order=3,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="What is the main advantage of using Server-Sent Events (SSE) over WebSockets?",
                    options=[
                        "SSE supports bidirectional communication",
                        "SSE is simpler for one-way server-to-client updates and works over standard HTTP",
                        "SSE has lower latency than WebSockets",
                        "SSE supports binary data natively"
                    ],
                    correct_option=1,
                    points=2,
                    difficulty=2,
                    sort_order=4,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="Which PostgreSQL feature is used to prevent duplicate rows based on specific columns?",
                    options=["FOREIGN KEY", "CHECK constraint", "UNIQUE constraint", "INDEX"],
                    correct_option=2,
                    points=1,
                    difficulty=1,
                    sort_order=5,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="What does 'idempotency' mean in the context of API design?",
                    options=[
                        "The API returns the same response format every time",
                        "Making the same request multiple times produces the same result as making it once",
                        "The API encrypts all requests",
                        "The API can only be called once per minute"
                    ],
                    correct_option=1,
                    points=2,
                    difficulty=2,
                    sort_order=6,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="Which data structure is most efficient for implementing a job queue?",
                    options=["Array", "Linked List", "Stack (LIFO)", "Queue (FIFO)"],
                    correct_option=3,
                    points=1,
                    difficulty=1,
                    sort_order=7,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="What is the purpose of database connection pooling?",
                    options=[
                        "To create unlimited connections",
                        "To reuse existing connections and reduce overhead",
                        "To encrypt database traffic",
                        "To backup the database automatically"
                    ],
                    correct_option=1,
                    points=1,
                    difficulty=1,
                    sort_order=8,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="In FastAPI, what does Pydantic provide?",
                    options=[
                        "Database ORM functionality",
                        "Data validation and serialization using Python type hints",
                        "Frontend templating",
                        "CSS styling"
                    ],
                    correct_option=1,
                    points=1,
                    difficulty=1,
                    sort_order=9,
                ),
                Question(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    question_text="Which of the following is NOT a characteristic of a good unit test?",
                    options=[
                        "It tests a single unit of logic in isolation",
                        "It depends on external services like databases",
                        "It runs quickly",
                        "It is deterministic"
                    ],
                    correct_option=1,
                    points=2,
                    difficulty=2,
                    sort_order=10,
                ),
            ]

            for q in questions:
                session.add(q)
            await session.commit()
            print(f"  Created {len(questions)} questions.")
        else:
            print("  Assessment already exists, skipping questions.")

        # ── Test Sessions ──
        sessions_data = [
            {
                "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
                "candidate_id": alex.id,
                "status": EnrollmentStatus.ASSIGNED,
                "application_status": ApplicationStatus.APPLIED,
                "created_at": datetime.utcnow(),
            },
            {
                "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
                "candidate_id": sarah.id,
                "status": EnrollmentStatus.IN_PROGRESS,
                "application_status": ApplicationStatus.ATTEMPTED,
                "started_at": datetime.utcnow() - timedelta(hours=2),
                "created_at": datetime.utcnow() - timedelta(days=1),
            },
            {
                "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
                "candidate_id": michael.id,
                "status": EnrollmentStatus.COMPLETED,
                "application_status": ApplicationStatus.SUBMITTED,
                "started_at": datetime.utcnow() - timedelta(hours=3),
                "submitted_at": datetime.utcnow() - timedelta(minutes=30),
                "created_at": datetime.utcnow() - timedelta(days=2),
            },
        ]

        created_count = 0
        for data in sessions_data:
            result = await session.execute(select(TestSession).where(TestSession.id == data["id"]))
            if not result.scalar_one_or_none():
                ts = TestSession(assessment_id=assessment.id, **data)
                session.add(ts)
                created_count += 1
        if created_count:
            await session.commit()
            print(f"  Created {created_count} test sessions.")
        else:
            print("  Test sessions already exist.")

        print("Seed completed.")


if __name__ == "__main__":
    asyncio.run(seed())
