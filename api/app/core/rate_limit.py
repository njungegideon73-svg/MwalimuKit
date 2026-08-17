"""Redis-backed rate limiter dependency (graceful degradation)."""
from __future__ import annotations

import structlog

from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core.config import settings

logger = structlog.get_logger()
_redis: Redis | None = None
_redis_failed = False


async def _get_redis() -> Redis | None:
    global _redis, _redis_failed
    if _redis_failed:
        return None
    if _redis is None:
        try:
            _redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
        except Exception:
            _redis_failed = True
            logger.warning("redis_unavailable", msg="Rate limiting disabled — Redis unreachable")
            return None
    return _redis


async def rate_limit_login(request: Request) -> None:
    """5 attempts per minute per IP on /auth/login."""
    redis = await _get_redis()
    if redis is None:
        return
    try:
        ip = request.client.host if request.client else "unknown"
        key = f"rl:login:{ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > 5:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again in a minute.")
    except HTTPException:
        raise
    except Exception:
        logger.warning("rate_limit_error", msg="Rate limit check failed, allowing request")


async def rate_limit_generate(request: Request) -> None:
    """10 AI generation requests per minute per IP."""
    redis = await _get_redis()
    if redis is None:
        return
    try:
        ip = request.client.host if request.client else "unknown"
        key = f"rl:generate:{ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > 10:
            raise HTTPException(status_code=429, detail="Too many requests. Please wait before generating again.")
    except HTTPException:
        raise
    except Exception:
        logger.warning("rate_limit_error", msg="Rate limit check failed, allowing request")
