"""Classes CRUD."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, SchoolAdminUser
from app.models.curriculum import LearningArea
from app.models.learner import Learner
from app.models.school_class import SchoolClass
from app.models.user import UserRole
from app.schemas.classes import ClassIn, ClassOut, LearnerOut
from app.utils.activity_logger import log_activity


router = APIRouter()


async def _resolve_learning_area_ids(
    db: AsyncSession, codes: list[str]
) -> list[UUID]:
    if not codes:
        return []
    rows = (
        await db.execute(
            select(LearningArea.id).where(LearningArea.code.in_(codes))
        )
    ).scalars().all()
    return list(rows)


@router.get("", response_model=list[ClassOut])
async def list_classes(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[ClassOut]:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.school_admin.value, UserRole.super_admin.value):
        rows = (
            await db.execute(
                select(SchoolClass)
                .where(SchoolClass.school_id == user.school_id, SchoolClass.deleted_at.is_(None))
                .order_by(SchoolClass.created_at.desc())
            )
        ).scalars().all()
    else:
        rows = (
            await db.execute(
                select(SchoolClass)
                .where(SchoolClass.teacher_id == user.id, SchoolClass.deleted_at.is_(None))
                .order_by(SchoolClass.created_at.desc())
            )
        ).scalars().all()

    all_la_ids = {la_id for c in rows for la_id in (c.learning_area_ids or [])}
    la_map: dict[str, str] = {}
    if all_la_ids:
        la_rows = (
            await db.execute(
                select(LearningArea.id, LearningArea.code).where(LearningArea.id.in_(all_la_ids))
            )
        ).all()
        la_map = {str(row[0]): row[1] for row in la_rows}

    return [_to_out_with_map(c, la_map) for c in rows]


@router.post("", response_model=ClassOut)
async def create_class(payload: ClassIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ClassOut:
    la_ids = await _resolve_learning_area_ids(db, payload.learning_area_codes)
    c = SchoolClass(
        id=uuid4(),
        school_id=user.school_id,
        teacher_id=user.id,
        name=payload.name,
        grade_level=payload.grade_level,
        learning_area_ids=la_ids,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="class.created",
        details={"name": c.name, "grade_level": c.grade_level},
    )
    return await _to_out_async(c, db)


@router.get("/{class_id}", response_model=ClassOut)
async def get_class(class_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ClassOut:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.school_admin.value, UserRole.super_admin.value):
        c = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id,
                    SchoolClass.school_id == user.school_id,
                    SchoolClass.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
    else:
        c = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id,
                    SchoolClass.teacher_id == user.id,
                    SchoolClass.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return await _to_out_async(c, db)


@router.get("/{class_id}/learners", response_model=list[LearnerOut])
async def list_class_learners(
    class_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[LearnerOut]:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.school_admin.value, UserRole.super_admin.value):
        c = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id,
                    SchoolClass.school_id == user.school_id,
                    SchoolClass.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
    else:
        c = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == class_id,
                    SchoolClass.teacher_id == user.id,
                    SchoolClass.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Class not found")

    rows = (
        await db.execute(
            select(Learner)
            .where(Learner.class_id == class_id, Learner.deleted_at.is_(None))
            .order_by(Learner.full_name)
        )
    ).scalars().all()
    return [
        LearnerOut(
            id=l.id,
            school_id=l.school_id,
            class_id=l.class_id,
            full_name=l.full_name,
            admission_no=l.admission_no,
            gender=l.gender,
            deleted_at=l.deleted_at.isoformat() if l.deleted_at else None,
        )
        for l in rows
    ]


async def _resolve_la_codes_from_ids(
    db: AsyncSession, la_ids: list[str | UUID]
) -> list[str]:
    if not la_ids:
        return []
    uuid_ids = [i if isinstance(i, UUID) else UUID(i) for i in la_ids if i]
    if not uuid_ids:
        return []
    rows = (
        await db.execute(
            select(LearningArea.code).where(LearningArea.id.in_(uuid_ids))
        )
    ).scalars().all()
    return list(rows)


async def _to_out_async(c: SchoolClass, db: AsyncSession) -> ClassOut:
    codes = await _resolve_la_codes_from_ids(db, c.learning_area_ids or [])
    return ClassOut(
        id=c.id,
        school_id=c.school_id,
        teacher_id=c.teacher_id,
        name=c.name,
        grade_level=c.grade_level,
        learning_area_codes=codes,
        deleted_at=c.deleted_at.isoformat() if c.deleted_at else None,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _to_out_with_map(c: SchoolClass, la_map: dict[str, str]) -> ClassOut:
    codes = [la_map[str(la_id)] for la_id in (c.learning_area_ids or []) if str(la_id) in la_map]
    return ClassOut(
        id=c.id,
        school_id=c.school_id,
        teacher_id=c.teacher_id,
        name=c.name,
        grade_level=c.grade_level,
        learning_area_codes=codes,
        deleted_at=c.deleted_at.isoformat() if c.deleted_at else None,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _to_out(c: SchoolClass) -> ClassOut:
    return ClassOut(
        id=c.id,
        school_id=c.school_id,
        teacher_id=c.teacher_id,
        name=c.name,
        grade_level=c.grade_level,
        learning_area_codes=[],
        deleted_at=c.deleted_at.isoformat() if c.deleted_at else None,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )
