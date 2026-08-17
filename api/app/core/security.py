"""Password hashing + JWT helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, ttl: timedelta, token_type: str, extra_claims: dict | None = None) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str, role: str | None = None, school_id: str | None = None) -> str:
    extra_claims = {}
    if role:
        extra_claims["role"] = role
    if school_id:
        extra_claims["school_id"] = school_id
    return _create_token(user_id, timedelta(minutes=settings.access_token_ttl_minutes), "access", extra_claims)


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(days=settings.refresh_token_ttl_days), "refresh")


def decode_token(token: str) -> dict:
    """Raise JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
