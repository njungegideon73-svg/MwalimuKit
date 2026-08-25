"""Rate limiting + account lockout (Redis-backed with graceful degradation).

If Redis is unreachable, counters fall back to an in-process store so
protections still apply per worker instance (dev, tests, degraded prod).
"""
from __future__ import annotations

import time

import structlog
from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core.config import settings
from app.core.metrics import inc_counter

logger = structlog.get_logger()
_redis: Redis | None = None
_redis_failed = False

# ── In-memory fallback store ────────────────────────────────────────────────
# {key: (count, expires_at_epoch)}
_memory: dict[str, tuple[int, float]] = {}


def _memory_incr(key: str, window_seconds: int) -> int:
    now = time.time()
    count, expires_at = _memory.get(key, (0, 0.0))
    if expires_at <= now:
        count, expires_at = 0, now + window_seconds
    count += 1
    _memory[key] = (count, expires_at)
    return count


def _memory_get(key: str) -> int:
    count, expires_at = _memory.get(key, (0, 0.0))
    return count if expires_at > time.time() else 0


def reset_rate_limits() -> None:
    """Test helper: wipe the in-process fallback store."""
    _memory.clear()


async def _get_redis() -> Redis | None:
    global _redis, _redis_failed
    if _redis_failed:
        return None
    if _redis is None:
        try:
            _redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)
            await _redis.ping()
        except Exception:
            _redis_failed = True
            logger.warning("redis_unavailable", msg="Falling back to in-process rate limit store")
            return None
    return _redis


async def _incr(key: str, window_seconds: int) -> int:
    """Increment a fixed-window counter; returns new count."""
    redis = await _get_redis()
    if redis is not None:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        return int(count)
    return _memory_incr(key, window_seconds)


def _throttle(scope: str, max_requests: int, window_seconds: int):
    """IP-based fixed-window throttle factory with graceful degradation."""

    async def _rate_limit(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{scope}:{ip}"
        try:
            count = await _incr(key, window_seconds)
        except Exception:
            logger.warning("rate_limit_error", msg="Rate limit check failed, allowing request")
            return
        if count > max_requests:
            inc_counter("mwalimukit_rate_limited_total", {"scope": scope})
            logger.warning(
                "security.rate_limited",
                scope=scope,
                ip=ip,
                count=count,
                path=request.url.path,
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again shortly.",
            )

    return _rate_limit


# Named endpoint throttles ────────────────────────────────────────────────────
rate_limit_login = _throttle("login", max_requests=settings.rate_limit_login_max, window_seconds=settings.rate_limit_login_window)
rate_limit_signup = _throttle("signup", max_requests=settings.rate_limit_signup_max, window_seconds=settings.rate_limit_signup_window)
rate_limit_refresh = _throttle("refresh", max_requests=30, window_seconds=60)
rate_limit_generate = _throttle("generate", max_requests=10, window_seconds=60)
rate_limit_password_change = _throttle("password", max_requests=10, window_seconds=60)
rate_limit_password_reset_request = _throttle("pwd_reset_req", max_requests=3, window_seconds=60)
rate_limit_password_reset = _throttle("pwd_reset", max_requests=5, window_seconds=60)

# ── Account lockout ──────────────────────────────────────────────────────────
LOCKOUT_MAX_FAILURES = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60
LOCKOUT_DURATION_SECONDS = 15 * 60


async def is_locked_out(email: str, ip: str) -> bool:
    """True when this (email, ip) pair has been locked out."""
    redis = await _get_redis()
    key = f"lock:{email.lower()}:{ip}"
    if redis is not None:
        try:
            locked = await redis.exists(key)
            return bool(locked)
        except Exception:
            pass
    return _memory_get(f"locked:{key}") > 0


async def is_locked_out_any_ip(email: str) -> bool:
    """True when this email has been locked out from any IP."""
    redis = await _get_redis()
    key = f"account_locked:{email.lower()}"
    if redis is not None:
        try:
            return await redis.exists(key) == 1
        except Exception:
            pass
    return _memory_get(key) > 0


async def register_login_failure(email: str, ip: str) -> int:
    """Count a failed attempt; locks the pair at the threshold. Returns count."""
    count = await _incr(f"fl:{email.lower()}:{ip}", LOCKOUT_WINDOW_SECONDS)
    if count >= LOCKOUT_MAX_FAILURES:
        await _apply_lockout(email, ip)
    return count


async def clear_login_failures(email: str, ip: str) -> None:
    redis = await _get_redis()
    if redis is not None:
        try:
            await redis.delete(f"fl:{email.lower()}:{ip}")
            await redis.delete(f"account_locked:{email.lower()}")
        except Exception:
            pass
    _memory.pop(f"fl:{email.lower()}:{ip}", None)
    _memory.pop(f"account_locked:{email.lower()}", None)


async def _apply_lockout(email: str, ip: str) -> None:
    key = f"lock:{email.lower()}:{ip}"
    redis = await _get_redis()
    if redis is not None:
        try:
            await redis.setex(key, LOCKOUT_DURATION_SECONDS, "1")
            await redis.setex(f"account_locked:{email.lower()}", LOCKOUT_DURATION_SECONDS, "1")
        except Exception:
            pass
    _memory_incr(f"locked:{key}", LOCKOUT_DURATION_SECONDS)
    _memory_incr(f"account_locked:{email.lower()}", LOCKOUT_DURATION_SECONDS)
    inc_counter("mwalimukit_lockouts_total")
    logger.warning("security.account_locked", email=email, ip=ip)


class GlobalThrottleMiddleware:
    """Coarse per-IP limiter applied to every route (defense in depth).

    Excludes health/readiness/metrics/docs endpoints. Degrades to no-op
    without Redis.
    """

    MAX_REQUESTS_PER_MINUTE = 300
    EXEMPT_PREFIXES = ("/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        ip = client[0] if client else "unknown"

        try:
            count = await _incr(f"rl:global:{ip}", 60)
        except Exception:
            count = 0  # never block traffic because the limiter itself failed

        if count > self.MAX_REQUESTS_PER_MINUTE:
            inc_counter("mwalimukit_rate_limited_total", {"scope": "global"})
            response = _json_response(
                429, {"detail": "Too many requests. Please slow down."}
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _json_response(status_code: int, content: dict):
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=content)


# ── User-based rate limiting ──────────────────────────────────────────────────


def make_user_rate_limiter(scope: str, max_requests: int, window_seconds: int):
    """Dependency factory: rate-limit by authenticated user ID.

    Usage in a router::

        from app.core.deps import CurrentUser
        _user_rl: None = Depends(make_user_rate_limiter("generate", 30, 60))

        @router.post("/generate", ...):
        async def generate(user: CurrentUser, _user_rl: None = Depends(...)):

    Falls back to IP-based limiting when the user is anonymous.
    """

    async def _rate_limit(user, request: Request) -> None:
        if user is not None and hasattr(user, "id"):
            key = f"rlu:{scope}:{user.id}"
        else:
            ip = request.client.host if request.client else "unknown"
            key = f"rl:{scope}:{ip}"
        try:
            count = await _incr(key, window_seconds)
        except Exception:
            return
        if count > max_requests:
            inc_counter("mwalimukit_user_rate_limited_total", {"scope": scope})
            raise HTTPException(
                status_code=429,
                detail="Too many requests for this action. Please slow down.",
            )

    return _rate_limit
