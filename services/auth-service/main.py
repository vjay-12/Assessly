import os
import uuid
import json
import hmac
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db, init_engine
from shared.models import User, UserRole, TestSession, ApplicationStatus, AuditLog, AuditEventType, AuditEventCategory, SeverityLevel
from shared.email import send_welcome_email, send_password_reset_email
from config import settings

app = FastAPI(title="Assessly Auth Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)

# Redis client
redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    await init_engine()


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


# ─── Pydantic Models ───

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CrossAppTokenRequest(BaseModel):
    application_id: str


class CrossAppTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    expires_in: int


class RedeemTokenRequest(BaseModel):
    token: str


class RedeemTokenResponse(BaseModel):
    session_token: str
    candidate_id: str
    application_id: str


class VerifyResponse(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    role: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "candidate"


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str


# ─── Helpers ───

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire, "iat": datetime.utcnow(), "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": user_id, "exp": expire, "iat": datetime.utcnow(), "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_assessment_session_token(candidate_id: str, application_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {
        "sub": candidate_id,
        "application_id": application_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "assessment_session"
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check token blocklist (logout)
    if redis_client:
        blocked = await redis_client.get(f"token:blocklist:{credentials.credentials}")
        if blocked:
            raise HTTPException(status_code=401, detail="Token revoked")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ─── Endpoints ───

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        db.add(AuditLog(
            event_type=AuditEventType.LOGIN_FAILED,
            category=AuditEventCategory.AUTH,
            severity=SeverityLevel.MEDIUM,
            details=f"Failed login attempt for email: {req.email}",
        ))
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        db.add(AuditLog(
            user_id=user.id,
            event_type=AuditEventType.LOGIN_FAILED,
            category=AuditEventCategory.AUTH,
            severity=SeverityLevel.MEDIUM,
            details=f"Failed login attempt for user: {user.email}",
        ))
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    db.add(AuditLog(
        user_id=user.id,
        event_type=AuditEventType.LOGIN,
        category=AuditEventCategory.AUTH,
        severity=SeverityLevel.INFORMATIONAL,
        details=f"User logged in: {user.email} ({user.role.value})",
    ))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


class LogoutResponse(BaseModel):
    message: str


@app.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        exp = payload.get("exp")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Add token to blocklist with TTL = remaining token lifetime
    if redis_client and exp:
        ttl = int(exp - datetime.utcnow().timestamp())
        if ttl > 0:
            await redis_client.setex(f"token:blocklist:{credentials.credentials}", ttl, "1")

    # Log logout event
    if user_id:
        db.add(AuditLog(
            user_id=uuid.UUID(user_id),
            event_type=AuditEventType.LOGOUT,
            category=AuditEventCategory.AUTH,
            severity=SeverityLevel.INFORMATIONAL,
            details=f"User logged out: {user_id}",
        ))
        await db.commit()

    return LogoutResponse(message="Logged out successfully")


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/cross-app-token", response_model=CrossAppTokenResponse)
async def mint_cross_app_token(
    req: CrossAppTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify the test session belongs to the candidate
    result = await db.execute(
        select(TestSession).where(
            TestSession.id == uuid.UUID(req.application_id),
            TestSession.candidate_id == current_user.id
        )
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=403, detail="Application not found")

    token_id = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)
    timestamp = datetime.utcnow().isoformat()

    binding = hmac.new(
        settings.cross_app_secret.encode(),
        f"{current_user.id}:{req.application_id}:{nonce}:{timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()

    payload = json.dumps({
        "candidate_id": str(current_user.id),
        "application_id": req.application_id,
        "nonce": nonce,
        "binding": binding,
        "used": False
    })

    await redis_client.setex(f"crossapp:{token_id}", settings.cross_app_token_expire_seconds, payload)

    return CrossAppTokenResponse(
        token=f"ca_{token_id}:{binding}",
        expires_at=datetime.utcnow() + timedelta(seconds=settings.cross_app_token_expire_seconds),
        expires_in=settings.cross_app_token_expire_seconds
    )


@app.post("/auth/redeem-cross-app", response_model=RedeemTokenResponse)
async def redeem_cross_app_token(req: RedeemTokenRequest, db: AsyncSession = Depends(get_db)):
    if not req.token.startswith("ca_"):
        raise HTTPException(status_code=400, detail="Invalid token format")

    parts = req.token[3:].split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid token format")

    token_id, provided_binding = parts

    raw = await redis_client.get(f"crossapp:{token_id}")
    if not raw:
        raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")

    payload = json.loads(raw)

    if payload.get("used"):
        raise HTTPException(status_code=410, detail="TOKEN_ALREADY_REDEEMED")

    if not hmac.compare_digest(payload["binding"], provided_binding):
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    # Atomic delete to ensure single-use
    await redis_client.delete(f"crossapp:{token_id}")

    session_token = create_assessment_session_token(
        payload["candidate_id"],
        payload["application_id"]
    )

    # Update test session application_status to ATTEMPTED
    result = await db.execute(
        select(TestSession).where(TestSession.id == uuid.UUID(payload["application_id"]))
    )
    session = result.scalar_one_or_none()
    if session and session.application_status not in [
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.EVALUATED,
    ]:
        was_first_attempt = session.application_status == ApplicationStatus.APPLIED
        session.application_status = ApplicationStatus.ATTEMPTED
        session.started_at = datetime.utcnow()
        await db.commit()

        if was_first_attempt:
            # Log assessment started only on first entry
            db.add(AuditLog(
                user_id=uuid.UUID(payload["candidate_id"]),
                event_type=AuditEventType.ASSESSMENT_STARTED,
                category=AuditEventCategory.ASSESSMENT_CANDIDATE,
                severity=SeverityLevel.INFORMATIONAL,
                assessment_id=session.assessment_id,
                details=f"Assessment started. Session: {payload['application_id']}",
            ))
            await db.commit()

    return RedeemTokenResponse(
        session_token=session_token,
        candidate_id=payload["candidate_id"],
        application_id=payload["application_id"]
    )


@app.get("/auth/verify", response_model=VerifyResponse)
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return VerifyResponse(valid=False)
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return VerifyResponse(valid=True, user_id=payload.get("sub"), role=payload.get("role"))
    except JWTError:
        return VerifyResponse(valid=False)


@app.post("/auth/register", response_model=RegisterResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == req.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate role
    role_str = (req.role or "candidate").lower()
    if role_str not in ("candidate", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'candidate' or 'admin'")
    role = UserRole.ADMIN if role_str == "admin" else UserRole.CANDIDATE

    # Hash password
    password_hash = (await asyncio.to_thread(bcrypt.hashpw, req.password.encode(), bcrypt.gensalt())).decode()

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

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))

    # Send welcome email asynchronously (fire-and-forget via asyncio)
    asyncio.create_task(asyncio.to_thread(send_welcome_email, user.email, user.full_name, req.password))

    return RegisterResponse(
        user_id=str(user.id),
        email=user.email,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@app.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        # Don't reveal whether email exists
        return ForgotPasswordResponse(message="If the email exists, a reset link has been sent")

    reset_token = secrets.token_urlsafe(32)
    await redis_client.setex(f"reset:{reset_token}", 3600, str(user.id))

    # Send password reset email asynchronously
    asyncio.create_task(asyncio.to_thread(send_password_reset_email, req.email, reset_token))

    return ForgotPasswordResponse(message="If the email exists, a reset link has been sent")


@app.post("/auth/reset-password", response_model=ResetPasswordResponse)
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    user_id = await redis_client.get(f"reset:{req.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = (await asyncio.to_thread(bcrypt.hashpw, req.new_password.encode(), bcrypt.gensalt())).decode()
    await db.commit()
    await redis_client.delete(f"reset:{req.token}")

    return ResetPasswordResponse(message="Password updated successfully")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}
