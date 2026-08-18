"""Learner CRUD."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, label
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.learner import Learner
from app.models.school_class import SchoolClass
from app.models.user import UserRole
from app.schemas.classes import LearnerBulkIn, LearnerIn, LearnerOut, LearnerUpdate, LearnerWithClassName
from app.utils.activity_logger import log_activity


router = APIRouter()


async def _class_owned(db: AsyncSession, user: "User", class_id: UUID) -> SchoolClass:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.school_admin.value, UserRole.super_admin.value):
        # School admins and super admins can access any class in their school
        c = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id, SchoolClass.school_id == user.school_id
                )
            )
        ).scalar_one_or_none()
    else:
        # Teachers can only access their own classes
        c = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id, SchoolClass.teacher_id == user.id
                )
            )
        ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return c


# Type hint for the User model to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User


@router.get("/by-class/{class_id}", response_model=list[LearnerOut])
async def list_for_class(
    class_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[LearnerOut]:
    await _class_owned(db, user, class_id)
    rows = (
        await db.execute(
            select(Learner)
            .where(Learner.class_id == class_id, Learner.deleted_at.is_(None))
            .order_by(Learner.full_name)
        )
    ).scalars().all()
    return [_to_out(l) for l in rows]


@router.get("/{learner_id}", response_model=LearnerWithClassName)
async def get_learner(
    learner_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> LearnerWithClassName:
    result = await db.execute(
        select(Learner, SchoolClass.name.label("class_name"))
        .join(SchoolClass, Learner.class_id == SchoolClass.id)
        .where(
            Learner.id == learner_id,
            Learner.school_id == user.school_id,
            Learner.deleted_at.is_(None),
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Learner not found")

    learner, class_name = row
    return LearnerWithClassName(
        id=learner.id,
        school_id=learner.school_id,
        class_id=learner.class_id,
        full_name=learner.full_name,
        admission_no=learner.admission_no,
        gender=learner.gender,
        deleted_at=learner.deleted_at.isoformat() if learner.deleted_at else None,
        class_name=class_name,
    )


@router.post("", response_model=LearnerOut)
async def add_learner(payload: LearnerIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> LearnerOut:
    await _class_owned(db, user, payload.class_id)
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
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="learner.created",
        details={"full_name": l.full_name, "class_id": str(l.class_id)},
    )
    return _to_out(l)


@router.post("/bulk", response_model=list[LearnerOut])
async def bulk_add(payload: LearnerBulkIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[LearnerOut]:
    await _class_owned(db, user, payload.class_id)
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
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="learner.bulk_created",
        details={"count": len(learners), "class_id": str(payload.class_id)},
    )
    return [_to_out(l) for l in learners]


@router.patch("/{learner_id}", response_model=LearnerOut)
async def update_learner(
    learner_id: UUID, payload: LearnerUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> LearnerOut:
    l = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if l is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    l.full_name = payload.full_name.strip()
    l.admission_no = payload.admission_no
    l.gender = payload.gender
    await db.commit()
    await db.refresh(l)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="learner.updated",
        details={"full_name": l.full_name},
    )
    return _to_out(l)


@router.delete("/{learner_id}")
async def delete_learner(
    learner_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    from datetime import datetime, timezone
    l = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == user.school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if l is None:
        raise HTTPException(status_code=404, detail="Learner not found")
    l.deleted_at = datetime.now(timezone.utc)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="learner.deleted",
        details={"full_name": l.full_name},
    )
    await db.commit()
    return {"ok": True}


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
