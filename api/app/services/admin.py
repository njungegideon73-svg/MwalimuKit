"""Shared admin business logic used by both the super-admin and school-admin routers."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.learner import Learner
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.user import User, UserRole


# ── Serializers ──────────────────────────────────────────────────────────────

def user_role_str(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def serialize_user(user: User) -> dict:
    """Shape shared by the super-admin UserOut and school-admin TeacherOut schemas."""
    return {
        "id": str(user.id),
        "school_id": str(user.school_id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user_role_str(user),
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


def serialize_learner(learner: Learner) -> dict:
    return {
        "id": str(learner.id),
        "school_id": str(learner.school_id),
        "class_id": str(learner.class_id),
        "full_name": learner.full_name,
        "admission_no": learner.admission_no,
        "gender": learner.gender,
        "deleted_at": learner.deleted_at.isoformat() if learner.deleted_at else None,
    }


def serialize_class(cls_obj: SchoolClass) -> dict:
    return {
        "id": str(cls_obj.id),
        "school_id": str(cls_obj.school_id),
        "teacher_id": str(cls_obj.teacher_id),
        "name": cls_obj.name,
        "grade_level": cls_obj.grade_level,
        "learning_area_codes": [],
        "deleted_at": cls_obj.deleted_at.isoformat() if cls_obj.deleted_at else None,
        "created_at": cls_obj.created_at.isoformat(),
        "updated_at": cls_obj.updated_at.isoformat(),
    }


def soft_delete_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Users ────────────────────────────────────────────────────────────────────

async def get_user(db: AsyncSession, user_id: str | UUID) -> User | None:
    return (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()


async def ensure_email_available(db: AsyncSession, email: str) -> None:
    existing = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Email already registered")


async def create_user(
    db: AsyncSession,
    *,
    school_id: UUID | str,
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
) -> User:
    await ensure_email_available(db, email)
    user = User(
        id=uuid4(),
        school_id=school_id,
        email=email,
        full_name=full_name,
        role=role,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def parse_role(role_value: str) -> UserRole:
    try:
        return UserRole(role_value)
    except ValueError as exc:
        raise ValueError(f"Invalid role: {role_value}") from exc


# ── Learners ─────────────────────────────────────────────────────────────────

async def get_active_learner(db: AsyncSession, learner_id: str | UUID) -> Learner | None:
    return (
        await db.execute(
            select(Learner).where(Learner.id == learner_id, Learner.deleted_at.is_(None))
        )
    ).scalar_one_or_none()


async def validate_class_in_school(
    db: AsyncSession, class_id: str | None, school_id: UUID | str | None = None
) -> None:
    """Ensure class_id exists (and belongs to school_id when given)."""
    if not class_id:
        return
    query = select(SchoolClass).where(SchoolClass.id == class_id)
    if school_id is not None:
        query = query.where(SchoolClass.school_id == school_id)
    cls_obj = (await db.execute(query)).scalar_one_or_none()
    if cls_obj is None:
        raise ValueError(
            "Class not found in your school" if school_id is not None else "Class not found"
        )


async def create_learner(
    db: AsyncSession,
    *,
    school_id: UUID | str,
    class_id: str | None = None,
    full_name: str,
    admission_no: str | None = None,
    gender: str | None = None,
) -> Learner:
    await validate_class_in_school(db, class_id, school_id)
    learner = Learner(
        id=uuid4(),
        school_id=school_id,
        class_id=class_id,
        full_name=full_name,
        admission_no=admission_no,
        gender=gender,
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    return learner


async def update_learner(
    db: AsyncSession,
    learner: Learner,
    *,
    school_id: str | None = None,
    class_id: str | None = None,
    full_name: str | None = None,
    admission_no: str | None = None,
    gender: str | None = None,
) -> Learner:
    if full_name is not None:
        learner.full_name = full_name
    if school_id is not None:
        learner.school_id = school_id
    if class_id is not None:
        learner.class_id = class_id
    if admission_no is not None:
        learner.admission_no = admission_no
    if gender is not None:
        learner.gender = gender
    await db.commit()
    await db.refresh(learner)
    return learner


async def soft_delete_learner(db: AsyncSession, learner: Learner) -> None:
    learner.deleted_at = soft_delete_now()
    await db.commit()


# ── Schools ──────────────────────────────────────────────────────────────────

async def get_school(db: AsyncSession, school_id: str | UUID) -> School | None:
    return (
        await db.execute(select(School).where(School.id == school_id))
    ).scalar_one_or_none()


async def ensure_school_code_available(
    db: AsyncSession, code: str, *, exclude_school_id: UUID | str | None = None
) -> None:
    query = select(School).where(School.code == code)
    if exclude_school_id is not None:
        query = query.where(School.id != exclude_school_id)
    existing = (await db.execute(query)).scalar_one_or_none()
    if existing is not None:
        raise ValueError("School code already exists")


async def create_school(
    db: AsyncSession,
    *,
    name: str,
    code: str,
    county: str | None = None,
    level: str | None = None,
) -> School:
    await ensure_school_code_available(db, code)
    school = School(id=uuid4(), name=name, code=code, county=county, level=level)
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school
