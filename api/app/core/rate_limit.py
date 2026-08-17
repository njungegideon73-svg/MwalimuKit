"""Redis-backed rate limiter dependency."""
from __future__ import annotations

import time

from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


async def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def rate_limit_login(request: Request) -> None:
    """5 attempts per minute per IP on /auth/login."""
    redis = await _get_redis()
    ip = request.client.host if request.client else "unknown"
    key = f"rl:login:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > 5:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in a minute.")


async def rate_limit_generate(request: Request) -> None:
    """10 AI generation requests per minute per IP."""
    redis = await _get_redis()
    ip = request.client.host if request.client else "unknown"
    key = f"rl:generate:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > 10:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait before generating again.")
