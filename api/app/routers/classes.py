"""Classes CRUD."""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.school_class import SchoolClass
from app.schemas.classes import ClassIn, ClassOut


router = APIRouter()


@router.get("", response_model=list[ClassOut])
async def list_classes(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[ClassOut]:
    rows = (
        await db.execute(
            select(SchoolClass)
            .where(SchoolClass.teacher_id == user.id, SchoolClass.deleted_at.is_(None))
            .order_by(SchoolClass.created_at.desc())
        )
    ).scalars().all()
    return [_to_out(c) for c in rows]


@router.post("", response_model=ClassOut)
async def create_class(payload: ClassIn, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ClassOut:
    c = SchoolClass(
        id=uuid4(),
        school_id=user.school_id,
        teacher_id=user.id,
        name=payload.name,
        grade_level=payload.grade_level,
        learning_area_ids=[],
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _to_out(c)


@router.get("/{class_id}", response_model=ClassOut)
async def get_class(class_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ClassOut:
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
    return _to_out(c)


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
