"""Assessment business logic — extracted from the router for testability."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentSource
from app.models.curriculum import LearningArea
from app.schemas.assessment import AssessmentIn, AssessmentOut, AssessmentUpdate


async def get_assessment_or_404(
    db: AsyncSession, assessment_id: UUID, school_id: UUID
) -> Assessment:
    from fastapi import HTTPException
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a


async def list_assessments(db: AsyncSession, school_id: UUID) -> list[AssessmentOut]:
    rows = (
        await db.execute(
            select(Assessment)
            .where(Assessment.school_id == school_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.updated_at.desc())
        )
    ).scalars().all()
    return [_to_out(a) for a in rows]


async def create_assessment(db: AsyncSession, payload: AssessmentIn, school_id: UUID, user_id: UUID) -> AssessmentOut:
    la = (
        await db.execute(select(LearningArea).where(LearningArea.code == payload.learning_area_code))
    ).scalar_one_or_none()
    if la is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Unknown learning_area_code")

    source = (
        AssessmentSource(payload.source)
        if payload.source in {s.value for s in AssessmentSource}
        else AssessmentSource.manual
    )
    a = Assessment(
        id=uuid4(),
        owner_id=user_id,
        school_id=school_id,
        learning_area_id=la.id,
        name=payload.name,
        description=payload.description,
        strand_code=payload.strand_code,
        sub_strand_codes=payload.sub_strand_codes,
        source=source,
        rubric=payload.rubric.model_dump(),
        items=[i.model_dump() for i in payload.items],
        tags=payload.tags,
        is_favourite=payload.is_favourite,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return await _to_out_async(a, db)


async def get_assessment(db: AsyncSession, assessment_id: UUID, school_id: UUID) -> AssessmentOut:
    a = await get_assessment_or_404(db, assessment_id, school_id)
    return await _to_out_async(a, db)


async def duplicate_assessment(db: AsyncSession, assessment_id: UUID, school_id: UUID, user_id: UUID) -> AssessmentOut:
    original = await get_assessment_or_404(db, assessment_id, school_id)
    dupe = Assessment(
        id=uuid4(),
        owner_id=user_id,
        school_id=school_id,
        learning_area_id=original.learning_area_id,
        name=f"{original.name} (copy)",
        description=original.description,
        strand_code=original.strand_code,
        sub_strand_codes=list(original.sub_strand_codes) if original.sub_strand_codes else [],
        source=original.source,
        rubric=dict(original.rubric),
        items=list(original.items),
        tags=list(original.tags),
        is_favourite=False,
    )
    db.add(dupe)
    await db.commit()
    await db.refresh(dupe)
    return await _to_out_async(dupe, db)


async def update_assessment(
    db: AsyncSession, assessment_id: UUID, school_id: UUID, payload: AssessmentUpdate
) -> AssessmentOut:
    a = await get_assessment_or_404(db, assessment_id, school_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "rubric" in update_data and update_data["rubric"] is not None:
        rubric_val = update_data["rubric"]
        if hasattr(rubric_val, "model_dump"):
            update_data["rubric"] = rubric_val.model_dump()
    if "items" in update_data and update_data["items"] is not None:
        update_data["items"] = [
            i.model_dump() if hasattr(i, "model_dump") else i
            for i in update_data["items"]
        ]

    for field, value in update_data.items():
        setattr(a, field, value)

    await db.commit()
    await db.refresh(a)
    return await _to_out_async(a, db)


async def toggle_favourite(db: AsyncSession, assessment_id: UUID, school_id: UUID) -> AssessmentOut:
    a = await get_assessment_or_404(db, assessment_id, school_id)
    a.is_favourite = not a.is_favourite
    await db.commit()
    await db.refresh(a)
    return await _to_out_async(a, db)


async def soft_delete(db: AsyncSession, assessment_id: UUID, school_id: UUID) -> dict:
    a = await get_assessment_or_404(db, assessment_id, school_id)
    a.deleted_at = datetime.now(tz=UTC)
    await db.commit()
    return {"deleted": True}


async def _to_out_async(a: Assessment, db: AsyncSession) -> AssessmentOut:
    la = (
        await db.execute(select(LearningArea).where(LearningArea.id == a.learning_area_id))
    ).scalar_one_or_none()
    return AssessmentOut(
        id=a.id,
        owner_id=a.owner_id,
        school_id=a.school_id,
        name=a.name,
        description=a.description,
        learning_area_code=la.code if la else "",
        strand_code=a.strand_code or "",
        sub_strand_codes=list(a.sub_strand_codes) if a.sub_strand_codes else [],
        source=a.source.value if hasattr(a.source, "value") else str(a.source),
        rubric=a.rubric,
        items=a.items,
        tags=a.tags,
        is_favourite=a.is_favourite,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
        deleted_at=a.deleted_at.isoformat() if a.deleted_at else None,
    )


def _to_out(a: Assessment) -> AssessmentOut:
    """Fallback for contexts where we don't need the learning area code."""
    return AssessmentOut(
        id=a.id,
        owner_id=a.owner_id,
        school_id=a.school_id,
        name=a.name,
        description=a.description,
        learning_area_code="",
        strand_code=a.strand_code or "",
        sub_strand_codes=list(a.sub_strand_codes) if a.sub_strand_codes else [],
        source=a.source.value if hasattr(a.source, "value") else str(a.source),
        rubric=a.rubric,
        items=a.items,
        tags=a.tags,
        is_favourite=a.is_favourite,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
        deleted_at=a.deleted_at.isoformat() if a.deleted_at else None,
    )
