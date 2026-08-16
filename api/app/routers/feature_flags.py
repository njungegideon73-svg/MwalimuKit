"""Public feature flags endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.feature_flag import FeatureFlag
from app.schemas.feature_flags import FeatureFlagsOut


router = APIRouter()


@router.get("/feature-flags", response_model=FeatureFlagsOut)
async def get_flags(db: AsyncSession = Depends(get_db)) -> FeatureFlagsOut:
    rows = (await db.execute(select(FeatureFlag))).scalars().all()
    raw = {r.key: r.value for r in rows}

    def _bool(key: str, default: bool) -> bool:
        v = raw.get(key, default)
        return bool(v) if v is not None else default

    def _int_or_none(key: str) -> int | None:
        v = raw.get(key)
        return int(v) if isinstance(v, (int, float)) else None

    return FeatureFlagsOut(
        paywall_enabled=_bool("paywall_enabled", False),
        ai_generation_enabled=_bool("ai_generation_enabled", True),
        max_classes=_int_or_none("max_classes"),
        max_learners_per_class=_int_or_none("max_learners_per_class"),
    )
