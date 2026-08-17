"""Assessment generation + CRUD."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_provider
from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.rate_limit import rate_limit_generate
from app.models.assessment import Assessment, AssessmentSource
from app.models.curriculum import LearningArea
from app.models.prompt_history import PromptHistory
from app.schemas.assessment import (
    AssessmentIn, AssessmentOut, AssessmentUpdate,
    GenerateAssessmentRequest, GenerateAssessmentResponse,
)


router = APIRouter()


@router.post("/generate", response_model=GenerateAssessmentResponse)
async def generate(
    request: Request,
    req: GenerateAssessmentRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_generate),
) -> GenerateAssessmentResponse:
    provider = get_provider()
    result = await provider.generate_assessment(
        learning_area=req.learning_area_code,
        strand=req.strand_code,
        sub_strand=", ".join(req.sub_strand_codes),
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
    )

    history = PromptHistory(
        user_id=user.id,
        school_id=user.school_id,
        learning_area_code=req.learning_area_code,
        strand_code=req.strand_code,
        sub_strand_codes=req.sub_strand_codes,
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
        response_rubric=result.rubric.model_dump() if hasattr(result.rubric, "model_dump") else result.rubric,
        response_items=[i.model_dump() for i in result.items] if hasattr(result.items[0], "model_dump") else result.items,
        provider=result.provider,
        model=result.model,
    )
    db.add(history)
    await db.commit()

    return GenerateAssessmentResponse(
        rubric=result.rubric,
        items=result.items,
        provider=result.provider,
        model=result.model,
    )


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[AssessmentOut]:
    rows = (
        await db.execute(
            select(Assessment)
            .where(Assessment.school_id == user.school_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.updated_at.desc())
        )
    ).scalars().all()
    return [_to_out(a) for a in rows]


@router.post("", response_model=AssessmentOut)
async def create_assessment(
    payload: AssessmentIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    la = (
        await db.execute(select(LearningArea).where(LearningArea.code == payload.learning_area_code))
    ).scalar_one_or_none()
    if la is None:
        raise HTTPException(status_code=400, detail="Unknown learning_area_code")

    source = AssessmentSource(payload.source) if payload.source in {s.value for s in AssessmentSource} else AssessmentSource.manual
    a = Assessment(
        id=uuid4(),
        owner_id=user.id,
        school_id=user.school_id,
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
    return _to_out(a)


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return _to_out(a)


@router.post("/{assessment_id}/duplicate", response_model=AssessmentOut)
async def duplicate_assessment(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    original = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    dupe = Assessment(
        id=uuid4(),
        owner_id=user.id,
        school_id=user.school_id,
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
    return _to_out(dupe)


@router.patch("/{assessment_id}", response_model=AssessmentOut)
async def update_assessment(
    assessment_id: UUID,
    payload: AssessmentUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

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


@router.post("/{assessment_id}/favourite", response_model=AssessmentOut)
async def toggle_favourite(
    assessment_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AssessmentOut:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    a.is_favourite = not a.is_favourite
    await db.commit()
    await db.refresh(a)
    return await _to_out_async(a, db)


@router.delete("/{assessment_id}")
async def soft_delete(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id, Assessment.school_id == user.school_id
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    a.deleted_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"deleted": True}


# --- alias for learning_area_code lookup ---
_la_cache: dict[str, str] = {}


def _resolve_la_code(db: AsyncSession, learning_area_id: UUID) -> str:
    """Synchronous placeholder — actual resolution happens in _to_out_async."""
    return ""


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
