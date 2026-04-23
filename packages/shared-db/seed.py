import asyncio
import os
import bcrypt
from uuid import uuid4
from datetime import datetime, timedelta
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, AsyncSessionLocal
from models import Base, User, UserRole, CandidateStatus, Application, ApplicationStatus, MCQQuestion

load_dotenv()


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create candidate users
        candidates = [
            User(
                id=uuid4(),
                email="alex.rivera@example.com",
                name="Alex Rivera",
                password_hash=bcrypt.hashpw("candidate123".encode(), bcrypt.gensalt()).decode(),
                role=UserRole.CANDIDATE,
                status=CandidateStatus.ACTIVE,
            ),
            User(
                id=uuid4(),
                email="sarah.jenkins@example.com",
                name="Sarah Jenkins",
                password_hash=bcrypt.hashpw("candidate123".encode(), bcrypt.gensalt()).decode(),
                role=UserRole.CANDIDATE,
                status=CandidateStatus.ACTIVE,
            ),
            User(
                id=uuid4(),
                email="michael.chen@example.com",
                name="Michael Chen",
                password_hash=bcrypt.hashpw("candidate123".encode(), bcrypt.gensalt()).decode(),
                role=UserRole.CANDIDATE,
                status=CandidateStatus.APPLIED,
            ),
        ]

        # Create employer user
        employer = User(
            id=uuid4(),
            email="hr@zetheta.com",
            name="HR Admin",
            password_hash=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
            role=UserRole.EMPLOYER,
            status=CandidateStatus.ACTIVE,
        )

        for u in candidates + [employer]:
            session.add(u)
        await session.commit()

        # Create sample applications
        app1 = Application(
            id=uuid4(),
            candidate_id=candidates[0].id,
            status=ApplicationStatus.APPLIED,
            created_at=datetime.utcnow(),
        )
        app2 = Application(
            id=uuid4(),
            candidate_id=candidates[1].id,
            status=ApplicationStatus.ATTEMPTED,
            started_at=datetime.utcnow() - timedelta(hours=2),
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        app3 = Application(
            id=uuid4(),
            candidate_id=candidates[2].id,
            status=ApplicationStatus.SUBMITTED,
            started_at=datetime.utcnow() - timedelta(hours=3),
            submitted_at=datetime.utcnow() - timedelta(minutes=30),
            created_at=datetime.utcnow() - timedelta(days=2),
        )

        for a in [app1, app2, app3]:
            session.add(a)
        await session.commit()

        # Create MCQ questions
        questions = [
            MCQQuestion(
                id=uuid4(),
                question_text="What is the primary purpose of an API Gateway in a microservices architecture?",
                options=[
                    "To store business logic",
                    "To route requests, enforce authentication, and aggregate responses",
                    "To replace the need for a database",
                    "To compile frontend assets"
                ],
                correct_option=1,
                difficulty=1,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="Which HTTP status code indicates a successful creation of a resource?",
                options=["200 OK", "201 Created", "204 No Content", "400 Bad Request"],
                correct_option=1,
                difficulty=1,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="In Python's asyncio, what does 'await' do?",
                options=[
                    "Pauses the entire program",
                    "Yields control back to the event loop until the awaited coroutine completes",
                    "Creates a new thread",
                    "Blocks the main thread synchronously"
                ],
                correct_option=1,
                difficulty=2,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="What is the main advantage of using Server-Sent Events (SSE) over WebSockets?",
                options=[
                    "SSE supports bidirectional communication",
                    "SSE is simpler for one-way server-to-client updates and works over standard HTTP",
                    "SSE has lower latency than WebSockets",
                    "SSE supports binary data natively"
                ],
                correct_option=1,
                difficulty=2,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="Which PostgreSQL feature is used to prevent duplicate rows based on specific columns?",
                options=["FOREIGN KEY", "CHECK constraint", "UNIQUE constraint", "INDEX"],
                correct_option=2,
                difficulty=1,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="What does 'idempotency' mean in the context of API design?",
                options=[
                    "The API returns the same response format every time",
                    "Making the same request multiple times produces the same result as making it once",
                    "The API encrypts all requests",
                    "The API can only be called once per minute"
                ],
                correct_option=1,
                difficulty=2,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="Which data structure is most efficient for implementing a job queue?",
                options=["Array", "Linked List", "Stack (LIFO)", "Queue (FIFO)"],
                correct_option=3,
                difficulty=1,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="What is the purpose of database connection pooling?",
                options=[
                    "To create unlimited connections",
                    "To reuse existing connections and reduce overhead",
                    "To encrypt database traffic",
                    "To backup the database automatically"
                ],
                correct_option=1,
                difficulty=1,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="In FastAPI, what does Pydantic provide?",
                options=[
                    "Database ORM functionality",
                    "Data validation and serialization using Python type hints",
                    "Frontend templating",
                    "CSS styling"
                ],
                correct_option=1,
                difficulty=1,
            ),
            MCQQuestion(
                id=uuid4(),
                question_text="Which of the following is NOT a characteristic of a good unit test?",
                options=[
                    "It tests a single unit of logic in isolation",
                    "It depends on external services like databases",
                    "It runs quickly",
                    "It is deterministic"
                ],
                correct_option=1,
                difficulty=2,
            ),
        ]

        for q in questions:
            session.add(q)
        await session.commit()

        print("✅ Seed completed: 3 candidates, 1 employer, 3 applications, 10 questions")


if __name__ == "__main__":
    asyncio.run(seed())
