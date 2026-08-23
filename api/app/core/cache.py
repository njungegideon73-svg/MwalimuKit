"""Redis-backed response caching for read-heavy endpoints.

Degrades gracefully to no-cache if Redis is unavailable.  Keys are
namespaced per endpoint so invalidation is trivial.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import structlog
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
            _redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)
            await _redis.ping()
        except Exception as exc:  # noqa: BLE001 — graceful degradation
            _redis_failed = True
            logger.warning("redis_cache_unavailable", reason=str(exc))
            return None
    return _redis


def _cache_key(prefix: str, *parts: str) -> str:
    return f"cache:{prefix}:{':'.join(parts)}"


async def cache_get(prefix: str, *parts: str) -> dict[str, Any] | None:
    redis = await _get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_cache_key(prefix, *parts))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        logger.warning("cache_read_failed", key=prefix, reason=str(exc))
        return None


async def cache_set(
    prefix: str,
    parts: tuple[str, ...],
    value: dict[str, Any],
    ttl: int = 300,
) -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        await redis.setex(_cache_key(prefix, *parts), ttl, json.dumps(value))
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        logger.warning("cache_write_failed", key=prefix, reason=str(exc))


async def cache_delete_pattern(prefix: str) -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        async for key in redis.scan_iter(f"cache:{prefix}:*"):
            await redis.delete(key)
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        logger.warning("cache_invalidation_failed", key=prefix, reason=str(exc))


async def invalidate_catalogue_cache() -> None:
    """Invalidate all cached curriculum catalogue entries."""
    await cache_delete_pattern("catalogue")


def cached(prefix: str, ttl: int = 300, key_parts: list[str] | None = None):
    """Decorator factory for caching async endpoint results."""
    def decorator(func: Callable):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Best-effort: derive key parts from the resolved user if present.
            request = kwargs.get("request")
            user = kwargs.get("user")
            parts: list[str] = []
            if request is not None:
                parts.append(request.url.path)
            if user is not None and hasattr(user, "school_id"):
                parts.append(str(user.school_id))
            if key_parts:
                for kp in key_parts:
                    val = kwargs.get(kp)
                    if val is not None:
                        parts.append(str(val))

            cached_val = await cache_get(prefix, *parts)
            if cached_val is not None:
                return cached_val

            result = await func(*args, **kwargs)
            # Only cache dict/list responses (Pydantic models included).
            if isinstance(result, (dict, list)):
                await cache_set(prefix, tuple(parts), result, ttl=ttl)
            return result

        return wrapper

    return decorator
