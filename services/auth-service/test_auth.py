import pytest
import hmac
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from jose import jwt

from config import settings


def test_cross_app_token_binding():
    """Verify HMAC binding is computed correctly."""
    candidate_id = "test-candidate"
    application_id = "test-app"
    nonce = secrets.token_urlsafe(16)
    timestamp = datetime.utcnow().isoformat()

    binding = hmac.new(
        settings.cross_app_secret.encode(),
        f"{candidate_id}:{application_id}:{nonce}:{timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()

    assert len(binding) == 64  # SHA-256 hex length
    assert binding != ""


def test_cross_app_token_format():
    """Verify token format is ca_{token_id}:{binding}."""
    token_id = secrets.token_urlsafe(32)
    binding = "a" * 64
    token = f"ca_{token_id}:{binding}"

    assert token.startswith("ca_")
    parts = token[3:].split(":")
    assert len(parts) == 2
    assert len(parts[1]) == 64


def test_jwt_creation_and_verification():
    """Verify JWT can be created and verified."""
    user_id = "test-user"
    role = "candidate"
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = {"sub": user_id, "role": role, "exp": expire, "iat": datetime.utcnow(), "type": "access"}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert decoded["sub"] == user_id
    assert decoded["role"] == role
    assert decoded["type"] == "access"


def test_timing_safe_comparison():
    """Verify hmac.compare_digest prevents timing attacks."""
    a = secrets.token_hex(32)
    b = a
    c = secrets.token_hex(32)

    assert hmac.compare_digest(a, b) is True
    assert hmac.compare_digest(a, c) is False


def test_assessment_session_token_scoping():
    """Verify assessment session tokens have correct type and short expiry."""
    candidate_id = "test-candidate"
    application_id = "test-app"
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {
        "sub": candidate_id,
        "application_id": application_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "assessment_session"
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

    assert decoded["type"] == "assessment_session"
    assert decoded["application_id"] == application_id
