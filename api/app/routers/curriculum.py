"""Curriculum router — returns the catalogue that the PWA caches.

The catalogue is global reference data (CBC strands / sub-strands) that
changes rarely, so it is served from a Redis-backed cache with a long
TTL.  Cache invalidation hooks are provided via the
``invalidate_catalogue_cache`` helper for use in migrations or seed scripts.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.curriculum import LearningArea, Strand, SubStrand
from app.schemas.curriculum import (
    CurriculumCatalogue,
    LearningAreaOut,
    StrandOut,
    SubStrandOut,
)

router = APIRouter()

_CATALOGUE_CACHE_PREFIX = "catalogue"


async def invalidate_catalogue_cache() -> None:
    """Drop the cached catalogue (call after seeding or schema changes)."""
    await cache_delete_pattern(_CATALOGUE_CACHE_PREFIX)


@router.get("/catalogue", response_model=CurriculumCatalogue)
async def get_catalogue(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    _ = user  # auth required so the catalogue is not a public dump

    cached = await cache_get(_CATALOGUE_CACHE_PREFIX, "v1")
    if cached is not None:
        return JSONResponse(content=cached)

    las = (await db.execute(select(LearningArea).order_by(LearningArea.sort_order))).scalars().all()
    ss = (await db.execute(select(Strand).order_by(Strand.sort_order))).scalars().all()
    subs = (await db.execute(select(SubStrand).order_by(SubStrand.sort_order))).scalars().all()

    la_map = {la.id: la for la in las}
    strand_map = {s.id: s for s in ss}

    result = CurriculumCatalogue(
        learning_areas=[
            LearningAreaOut(id=str(la.id), code=la.code, name=la.name, level=la.level.value, sort_order=la.sort_order)
            for la in las
        ],
        strands=[
            StrandOut(
                code=s.code,
                learning_area_code=la_map[s.learning_area_id].code,
                name=s.name,
                sort_order=s.sort_order,
            )
            for s in ss
            if s.learning_area_id in la_map
        ],
        sub_strands=[
            SubStrandOut(
                code=ss_obj.code,
                strand_code=strand_map[ss_obj.strand_id].code,
                name=ss_obj.name,
                sort_order=ss_obj.sort_order,
            )
            for ss_obj in subs
            if ss_obj.strand_id in strand_map
        ],
    )

    payload = result.model_dump()
    await cache_set(_CATALOGUE_CACHE_PREFIX, ("v1",), payload, ttl=settings.cache_ttl_seconds)
    return result
