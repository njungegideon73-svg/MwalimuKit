"""Learner CRUD."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.learner import Learner
from app.models.school_class import SchoolClass
from app.schemas.classes import LearnerBulkIn, LearnerIn, LearnerOut


router = APIRouter()


async def _class_owned(db: AsyncSession, teacher_id: UUID, class_id: UUID) -> SchoolClass:
    c = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == class_id, SchoolClass.teacher_id == teacher_id
            )
        )
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return c


@router.get("/by-class/{class_id}", response_model=list[LearnerOut])
async def list_for_class(
    class_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[LearnerOut]:
    await _class_owned(db, user.id, class_id)
    rows = (
        await db.execute(
            select(Learner)
            .where(Learner.class_id == class_id, Learner.deleted_at.is_(None))
            .order_by(Learner.full_name)
        )
    ).scalars().all()
    return [_to_out(l) for l in rows]


@router.post("", response_model=LearnerOut)
async def add_learner(payload: LearnerIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> LearnerOut:
    await _class_owned(db, user.id, payload.class_id)
    l = Learner(
        id=uuid4(),
        school_id=user.school_id,
        class_id=payload.class_id,
        full_name=payload.full_name.strip(),
        admission_no=payload.admission_no,
        gender=payload.gender,
    )
    db.add(l)
    await db.commit()
    await db.refresh(l)
    return _to_out(l)


@router.post("/bulk", response_model=list[LearnerOut])
async def bulk_add(payload: LearnerBulkIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[LearnerOut]:
    await _class_owned(db, user.id, payload.class_id)
    learners: list[Learner] = []
    for raw in payload.lines:
        raw = raw.strip()
        if not raw:
            continue
        if "," in raw:
            name, _, adm = raw.partition(",")
            adm = adm.strip() or None
        else:
            name, adm = raw, None
        l = Learner(
            id=uuid4(),
            school_id=user.school_id,
            class_id=payload.class_id,
            full_name=name.strip(),
            admission_no=adm,
        )
        db.add(l)
        learners.append(l)
    await db.commit()
    for l in learners:
        await db.refresh(l)
    return [_to_out(l) for l in learners]


def _to_out(l: Learner) -> LearnerOut:
    return LearnerOut(
        id=l.id,
        school_id=l.school_id,
        class_id=l.class_id,
        full_name=l.full_name,
        admission_no=l.admission_no,
        gender=l.gender,
        deleted_at=l.deleted_at.isoformat() if l.deleted_at else None,
    )
