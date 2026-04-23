import pytest
from jose import jwt
from datetime import datetime, timedelta
from config import settings


def test_jwt_verification():
    """Verify gateway can validate assessment session tokens."""
    payload = {
        "sub": "test-user",
        "application_id": "test-app",
        "exp": datetime.utcnow() + timedelta(minutes=5),
        "iat": datetime.utcnow(),
        "type": "assessment_session"
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert decoded["type"] == "assessment_session"


def test_funnel_calculation():
    """Verify funnel counts are computed correctly."""
    counts = {"applied": 10, "attempted": 8, "submitted": 6, "evaluated": 5}

    applied = counts.get("applied", 0) + counts.get("attempted", 0) + counts.get("submitted", 0) + counts.get("evaluated", 0)
    attempted = counts.get("attempted", 0) + counts.get("submitted", 0) + counts.get("evaluated", 0)
    submitted = counts.get("submitted", 0) + counts.get("evaluated", 0)
    evaluated = counts.get("evaluated", 0)

    assert applied == 29
    assert attempted == 19
    assert submitted == 11
    assert evaluated == 5
