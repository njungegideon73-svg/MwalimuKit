"""Auth business logic."""
from __future__ import annotations

import time
from uuid import uuid4

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import _get_redis, _memory
from app.core.sanitization import sanitize_dict
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.sessions import create_session, revoke_session, revoke_all_sessions
from app.models.school import School
from app.models.user import User, UserRole
from app.schemas.auth import SignupRequest, TokenPair, UserOut


async def _is_refresh_revoked(jti: str) -> bool:
    """Check the revocation list for a revoked refresh-token jti.

    Uses Redis when available, with an in-process fallback for dev/test.
    """
    if not settings.refresh_token_rotation:
        return False
    redis = await _get_redis()
    if redis is not None:
        try:
            return await redis.exists(f"revoked_refresh:{jti}") == 1
        except Exception:
            pass
    # In-process fallback
    val = _memory.get(f"revoked_refresh:{jti}")
    if val is None:
        return False
    _, expires_at = val
    if expires_at <= time.time():
        _memory.pop(f"revoked_refresh:{jti}", None)
        return False
    return True


async def _revoke_refresh(jti: str) -> None:
    """Add a refresh-token jti to the revocation list with TTL.

    Uses Redis when available, with an in-process fallback for dev/test.
    """
    if not settings.refresh_token_rotation:
        return
    redis = await _get_redis()
    ttl = settings.refresh_token_ttl_days * 24 * 60 * 60
    if redis is not None:
        try:
            await redis.setex(f"revoked_refresh:{jti}", ttl, "1")
            return
        except Exception:
            pass
    # In-process fallback
    _memory[f"revoked_refresh:{jti}"] = (1, time.time() + ttl)


async def signup(db: AsyncSession, payload: SignupRequest, user_agent: str | None = None) -> TokenPair:
    school = (
        await db.execute(select(School).where(School.code == payload.school_code))
    ).scalar_one_or_none()
    if school is None:
        raise ValueError("School code not found. Ask your school admin for the join code.")

    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Email already registered. Try logging in.")

    user = User(
        id=uuid4(),
        school_id=school.id,
        email=payload.email,
        full_name=payload.full_name,
        role=UserRole.teacher,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return await _pair_with_session(user, user_agent)


async def login(db: AsyncSession, *, email: str, password: str, user_agent: str | None = None) -> TokenPair:
    user = (
        await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password.")
    return await _pair_with_session(user, user_agent)


async def refresh_tokens(db: AsyncSession, refresh_token: str, user_agent: str | None = None) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:
        raise ValueError("Invalid or expired refresh token.") from exc

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type.")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload.")

    jti = payload.get("jti")
    if jti and await _is_refresh_revoked(jti):
        raise ValueError("Refresh token has been revoked.")

    user = (
        await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None:
        raise ValueError("User not found or deactivated.")

    if payload.get("ver", 0) != user.token_version:
        raise ValueError("Session has been revoked. Please log in again.")

    if jti:
        await _revoke_refresh(jti)

    return await _pair_with_session(user, user_agent)


async def _pair_with_session(user: User, user_agent: str | None = None) -> TokenPair:
    """Create a token pair and register a server-side session."""
    pair = _pair(user)
    # Extract the refresh-token jti to bind the session to it.
    try:
        payload = decode_token(pair.refresh_token)
        jti = payload.get("jti")
    except JWTError:
        jti = None
    await create_session(str(user.id), jti)
    return pair


def _pair(user: User) -> TokenPair:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return TokenPair(
        access_token=create_access_token(
            str(user.id), role=role, school_id=str(user.school_id), token_version=user.token_version
        ),
        refresh_token=create_refresh_token(str(user.id), token_version=user.token_version),
        user=UserOut(
            id=user.id,
            school_id=user.school_id,
            email=user.email,
            full_name=user.full_name,
            role=role,
        ),
    )


pair_for_user = _pair_with_session
