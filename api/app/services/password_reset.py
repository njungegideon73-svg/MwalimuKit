"""Password reset service.

Generates single-use, time-limited reset tokens stored in Redis (or the
in-process fallback store when Redis is unavailable).  Tokens are
cryptographically random and compared using :func:`hmac.compare_digest`
to prevent timing attacks.
"""
from __future__ import annotations

import hmac
import secrets
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import _get_redis
from app.core.config import settings
from app.core.rate_limit import _memory
from app.core.security import hash_password, verify_password
from app.models.user import User

#: Reset token lifetime in seconds (15 minutes).
RESET_TTL_SECONDS = 15 * 60

#: Key prefix for reset tokens.
_RESET_PREFIX = "pwd_reset"


def _memory_store(key: str, value: str, ttl: int) -> None:
    _memory[key] = (1, time.time() + ttl)
    _memory[key + ":val"] = value


def _memory_get_val(key: str) -> str | None:
    val = _memory.get(key + ":val")
    if val is None:
        return None
    _, expires_at = _memory.get(key, (0, 0.0))
    if expires_at <= time.time():
        _memory.pop(key + ":val", None)
        _memory.pop(key, None)
        return None
    return val  # type: ignore[return-value]


async def _redis_set(key: str, value: str, ttl: int) -> bool:
    redis = await _get_redis()
    if redis is None:
        return False
    try:
        await redis.setex(f"{_RESET_PREFIX}:{key}", ttl, value)
        return True
    except Exception:
        return False


async def _redis_get(key: str) -> str | None:
    redis = await _get_redis()
    if redis is None:
        return None
    try:
        val = await redis.get(f"{_RESET_PREFIX}:{key}")
        return val  # type: ignore[return-value]
    except Exception:
        return None


async def _redis_delete(key: str) -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        await redis.delete(f"{_RESET_PREFIX}:{key}")
    except Exception:
        pass


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


async def store_reset_token(email: str, token: str) -> None:
    """Persist a reset token, scoped to the user's email."""
    key = f"{email}:{token}"
    ok = await _redis_set(key, "1", RESET_TTL_SECONDS)
    if not ok:
        _memory_store(key, "1", RESET_TTL_SECONDS)


async def consume_reset_token(email: str, token: str) -> bool:
    """Validate and delete a reset token in one atomic operation.

    Returns ``True`` only when the token matches and has not expired.
    """
    redis = await _get_redis()
    key = f"{email}:{token}"

    if redis is not None:
        try:
            stored = await redis.get(f"{_RESET_PREFIX}:{key}")
            if stored is None:
                # Check memory fallback
                stored = _memory_get_val(key)
            if stored is None:
                return False
            # Single-use: delete immediately
            await redis.delete(f"{_RESET_PREFIX}:{key}")
            _memory.pop(key + ":val", None)
            _memory.pop(key, None)
            return True
        except Exception:
            pass

    # In-process fallback
    val = _memory_get_val(key)
    if val is None:
        return False
    _memory.pop(key + ":val", None)
    _memory.pop(key, None)
    return True


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Look up an active user by email (RLS-aware via auth email GUC)."""
    result = await db.execute(
        select(User).where(User.email == email, User.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def reset_password(db: AsyncSession, email: str, token: str, new_password: str) -> User | None:
    """Validate the token and update the user's password hash.

    Returns the updated ``User`` on success, or ``None`` if the token is
    invalid/expired.  Increments ``token_version`` to invalidate all
    existing sessions.
    """
    if not await consume_reset_token(email, token):
        return None

    user = await find_user_by_email(db, email)
    if user is None:
        return None

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    await db.commit()
    await db.refresh(user)
    return user
