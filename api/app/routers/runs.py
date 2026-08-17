"""Assessment runs (a session of an assessment against a class)."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass
from app.models.user import UserRole
from app.schemas.run_score import RunIn, RunOut


router = APIRouter()


async def _resolve_class(db: AsyncSession, user, class_id: UUID) -> SchoolClass:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.school_admin.value, UserRole.super_admin.value):
        cls = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id, SchoolClass.school_id == user.school_id
                )
            )
        ).scalar_one_or_none()
    else:
        cls = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id, SchoolClass.teacher_id == user.id
                )
            )
        ).scalar_one_or_none()
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.post("", response_model=RunOut)
async def start_run(payload: RunIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    cls = await _resolve_class(db, user, payload.class_id)

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


@router.get("", response_model=list[RunOut])
async def list_runs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    class_id: UUID | None = Query(default=None),
) -> list[RunOut]:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    stmt = select(AssessmentRun).where(AssessmentRun.school_id == user.school_id)
    if user_role not in (UserRole.school_admin.value, UserRole.super_admin.value):
        # Teachers can only see runs for their own classes
        stmt = stmt.join(SchoolClass, AssessmentRun.class_id == SchoolClass.id).where(
            SchoolClass.teacher_id == user.id
        )
    if class_id:
        stmt = stmt.where(AssessmentRun.class_id == class_id)
    stmt = stmt.order_by(AssessmentRun.started_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    stmt = select(AssessmentRun).where(
        AssessmentRun.id == run_id, AssessmentRun.school_id == user.school_id
    )
    if user_role not in (UserRole.school_admin.value, UserRole.super_admin.value):
        stmt = stmt.join(SchoolClass, AssessmentRun.class_id == SchoolClass.id).where(
            SchoolClass.teacher_id == user.id
        )
    r = (await db.execute(stmt)).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_out(r)


@router.post("/{run_id}/close", response_model=RunOut)
async def close_run(run_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> RunOut:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    stmt = select(AssessmentRun).where(
        AssessmentRun.id == run_id, AssessmentRun.school_id == user.school_id
    )
    if user_role not in (UserRole.school_admin.value, UserRole.super_admin.value):
        stmt = stmt.join(SchoolClass, AssessmentRun.class_id == SchoolClass.id).where(
            SchoolClass.teacher_id == user.id
        )
    r = (await db.execute(stmt)).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if r.closed_at is not None:
        raise HTTPException(status_code=400, detail="Run already closed")
    r.closed_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(r)
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
