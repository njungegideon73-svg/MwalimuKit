"""Curriculum router — returns the catalogue that the PWA caches."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.curriculum import LearningArea, Strand, SubStrand
from app.schemas.curriculum import (
    CurriculumCatalogue, LearningAreaOut, StrandOut, SubStrandOut,
)


router = APIRouter()


@router.get("/catalogue", response_model=CurriculumCatalogue)
async def get_catalogue(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> CurriculumCatalogue:
    _ = user  # auth required so the catalogue is not a public dump
    las = (await db.execute(select(LearningArea).order_by(LearningArea.sort_order))).scalars().all()
    ss = (await db.execute(select(Strand).order_by(Strand.sort_order))).scalars().all()
    subs = (await db.execute(select(SubStrand).order_by(SubStrand.sort_order))).scalars().all()

    la_map = {la.id: la for la in las}
    strand_map = {s.id: s for s in ss}

    return CurriculumCatalogue(
        learning_areas=[
            LearningAreaOut(code=la.code, name=la.name, level=la.level.value, sort_order=la.sort_order)
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
