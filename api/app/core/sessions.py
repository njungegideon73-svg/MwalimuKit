"""Server-side session management.

Tracks active user sessions in Redis so that administrators can:
- List a user's active sessions.
- Revoke individual sessions (single device logout).
- Enforce a concurrent-session limit.

Falls back to an in-process store when Redis is unavailable (single-worker
dev/test deployments only).
"""
from __future__ import annotations

import time
import uuid

from app.core.cache import _get_redis
from app.core.rate_limit import _memory

MAX_CONCURRENT_SESSIONS = 5
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days (matches refresh token TTL)

_SESSION_PREFIX = "session"


async def _redis():
    return await _get_redis()


def _sess_key(user_id: str, session_id: str) -> str:
    return f"{_SESSION_PREFIX}:{user_id}:{session_id}"


async def create_session(user_id: str, refresh_jti: str | None = None) -> str:
    """Register a new session for *user_id* and return its opaque ID.

    If the user already has ``MAX_CONCURRENT_SESSIONS`` active sessions,
    the oldest one is evicted.
    """
    session_id = uuid.uuid4().hex

    redis = await _redis()
    if redis is not None:
        try:
            pipe = redis.pipeline()
            pipe.sadd(f"{_SESSION_PREFIX}:user:{user_id}", session_id)
            pipe.setex(_sess_key(user_id, session_id), SESSION_TTL_SECONDS, refresh_jti or "1")
            pipe.sadd(f"{_SESSION_PREFIX}:user:{user_id}:set", session_id)
            existing = await redis.smembers(f"{_SESSION_PREFIX}:user:{user_id}")
            if len(existing) > MAX_CONCURRENT_SESSIONS:
                # Evict the oldest session (rough LRU by id order — production
                # would use a ZSET with timestamps).
                sorted_sessions = sorted(existing)
                for old_sid in sorted_sessions[: len(existing) - MAX_CONCURRENT_SESSIONS]:
                    old_key = _sess_key(user_id, old_sid)
                    pipe.delete(old_key)
                    pipe.srem(f"{_SESSION_PREFIX}:user:{user_id}", old_sid)
            await pipe.execute()
            return session_id
        except Exception:
            pass

    # In-process fallback
    bucket = _memory.setdefault(f"sessions:{user_id}", [])
    bucket.append((session_id, time.time() + SESSION_TTL_SECONDS))
    if len(bucket) > MAX_CONCURRENT_SESSIONS:
        bucket.pop(0)  # evict oldest
    return session_id


async def revoke_session(user_id: str, session_id: str) -> bool:
    """Revoke a single session. Returns True if the session existed."""
    redis = await _redis()
    if redis is not None:
        try:
            key = _sess_key(user_id, session_id)
            existed = await redis.delete(key)
            await redis.srem(f"{_SESSION_PREFIX}:user:{user_id}", session_id)
            return bool(existed)
        except Exception:
            pass

    bucket = _memory.get(f"sessions:{user_id}", [])
    for i, (sid, _exp) in enumerate(bucket):
        if sid == session_id:
            bucket.pop(i)
            return True
    return False


async def revoke_all_sessions(user_id: str) -> int:
    """Revoke every session for *user_id*. Returns count of revoked sessions."""
    redis = await _redis()
    if redis is not None:
        try:
            sids = await redis.smembers(f"{_SESSION_PREFIX}:user:{user_id}")
            if not sids:
                return 0
            pipe = redis.pipeline()
            for sid in sids:
                pipe.delete(_sess_key(user_id, sid))
            pipe.delete(f"{_SESSION_PREFIX}:user:{user_id}")
            await pipe.execute()
            return len(sids)
        except Exception:
            pass

    bucket = _memory.pop(f"sessions:{user_id}", [])
    return len(bucket)


async def list_sessions(user_id: str) -> list[dict]:
    """Return active sessions for *user_id*."""
    redis = await _redis()
    if redis is not None:
        try:
            sids = await redis.smembers(f"{_SESSION_PREFIX}:user:{user_id}")
            result = []
            for sid in sids:
                info = await redis.get(_sess_key(user_id, sid))
                if info:
                    result.append({"session_id": sid, "created_or_refreshed": None, "refresh_jti": info})
            return result
        except Exception:
            pass

    bucket = _memory.get(f"sessions:{user_id}", [])
    return [{"session_id": sid, "refresh_jti": None} for sid, _ in bucket]
