"""AI prompt history router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.prompt_history import PromptHistory

router = APIRouter()


class PromptHistoryIn(BaseModel):
    assessment_id: str | None = None
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str] = []
    grade_level: str
    teacher_prompt: str | None = None
    item_count: int = 5
    response_rubric: dict | None = None
    response_items: list | None = None
    provider: str
    model: str


class PromptHistoryOut(BaseModel):
    id: UUID
    assessment_id: UUID | None
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str]
    grade_level: str
    teacher_prompt: str | None
    item_count: int
    provider: str
    model: str
    feedback: str | None
    created_at: str


class FeedbackIn(BaseModel):
    feedback: str = Field(min_length=1, max_length=500)


@router.get("", response_model=list[PromptHistoryOut])
async def list_history(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> list[PromptHistoryOut]:
    rows = (
        await db.execute(
            select(PromptHistory)
            .where(PromptHistory.user_id == user.id)
            .order_by(PromptHistory.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [_to_out(h) for h in rows]


@router.post("", response_model=PromptHistoryOut)
async def save_history(
    payload: PromptHistoryIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PromptHistoryOut:
    h = PromptHistory(
        user_id=user.id,
        school_id=user.school_id,
        assessment_id=payload.assessment_id,
        learning_area_code=payload.learning_area_code,
        strand_code=payload.strand_code,
        sub_strand_codes=payload.sub_strand_codes,
        grade_level=payload.grade_level,
        teacher_prompt=payload.teacher_prompt,
        item_count=payload.item_count,
        response_rubric=payload.response_rubric,
        response_items=payload.response_items,
        provider=payload.provider,
        model=payload.model,
    )
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return _to_out(h)


@router.post("/{history_id}/feedback", response_model=PromptHistoryOut)
async def add_feedback(
    history_id: UUID,
    payload: FeedbackIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PromptHistoryOut:
    h = (
        await db.execute(
            select(PromptHistory).where(
                PromptHistory.id == history_id,
                PromptHistory.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if h is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    h.feedback = payload.feedback
    await db.commit()
    await db.refresh(h)
    return _to_out(h)


def _to_out(h: PromptHistory) -> PromptHistoryOut:
    return PromptHistoryOut(
        id=h.id,
        assessment_id=h.assessment_id,
        learning_area_code=h.learning_area_code,
        strand_code=h.strand_code,
        sub_strand_codes=list(h.sub_strand_codes) if h.sub_strand_codes else [],
        grade_level=h.grade_level,
        teacher_prompt=h.teacher_prompt,
        item_count=h.item_count,
        provider=h.provider,
        model=h.model,
        feedback=h.feedback,
        created_at=h.created_at.isoformat(),
    )
