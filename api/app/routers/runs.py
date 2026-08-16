"""Assessment runs (a session of an assessment against a class)."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass
from app.schemas.run_score import RunIn, RunOut


router = APIRouter()


@router.post("", response_model=RunOut)
async def start_run(payload: RunIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    cls = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == payload.class_id, SchoolClass.teacher_id == user.id
            )
        )
    ).scalar_one_or_none()
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")

    a = (
        await db.execute(
            select(Assessment).where(
                Assessment.id == payload.assessment_id,
                Assessment.school_id == user.school_id,
                Assessment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    r = AssessmentRun(
        id=uuid4(),
        school_id=user.school_id,
        class_id=payload.class_id,
        assessment_id=payload.assessment_id,
        term=payload.term,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _to_out(r)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    r = (
        await db.execute(
            select(AssessmentRun).where(
                AssessmentRun.id == run_id, AssessmentRun.school_id == user.school_id
            )
        )
    ).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_out(r)


def _to_out(r: AssessmentRun) -> RunOut:
    return RunOut(
        id=r.id,
        school_id=r.school_id,
        class_id=r.class_id,
        assessment_id=r.assessment_id,
        term=r.term,
        started_at=r.started_at.isoformat(),
        closed_at=r.closed_at.isoformat() if r.closed_at else None,
    )
