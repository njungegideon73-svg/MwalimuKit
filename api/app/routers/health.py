"""Healthcheck endpoints."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.metrics import inc_business_counter
from app.core.rate_limit import _get_redis

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness probe: process is up. No external dependencies checked."""
    inc_business_counter("health_check_liveness_total")
    return {"status": "ok", "service": "mwalimukit-api", "version": "0.1.0"}


@router.get("/ready")
async def ready(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe: verifies the API can reach its backing services."""
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {type(exc).__name__}"

    redis = await _get_redis()
    if redis is None:
        if settings.redis_url:
            checks["redis"] = "degraded"
        else:
            checks["redis"] = "not_configured"
    else:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {type(exc).__name__}"

    ready_ok = checks.get("db") == "ok"
    if not ready_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ready_ok else "unavailable", "checks": checks}
