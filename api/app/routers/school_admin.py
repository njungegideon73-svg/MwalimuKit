"""School admin router - School-scoped management."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import SchoolAdminUser, CurrentUser
from app.core.security import hash_password
from app.models.learner import Learner
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.user import User, UserRole
from app.schemas.classes import LearnerOut, ClassOut


router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class TeacherCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TeacherUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


class TeacherOut(BaseModel):
    id: str
    school_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class LearnerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    class_id: str | None = None
    admission_no: str | None = None
    gender: str | None = None


class LearnerBulkCreate(BaseModel):
    class_id: str
    lines: list[str] = Field(min_length=1)


class LearnerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    class_id: str | None = None
    admission_no: str | None = None
    gender: str | None = None


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade_level: str = Field(min_length=1, max_length=16)
    teacher_id: str | None = None


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    grade_level: str | None = Field(default=None, min_length=1, max_length=16)
    teacher_id: str | None = None


class SchoolStats(BaseModel):
    total_teachers: int
    total_learners: int
    total_classes: int


# ── Helper ───────────────────────────────────────────────────────────────────

def _require_school(user: User):
    """Ensure user belongs to a school."""
    if not user.school_id:
        raise HTTPException(status_code=400, detail="User not assigned to a school")
    return user.school_id


# ── Teacher Management ──────────────────────────────────────────────────────

@router.get("/teachers", response_model=list[TeacherOut])
async def list_teachers(
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TeacherOut]:
    school_id = _require_school(admin)
    query = (
        select(User)
        .where(User.school_id == school_id, User.role == UserRole.teacher)
        .order_by(User.created_at.desc())
    )
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    query = query.offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return [
        TeacherOut(
            id=str(u.id),
            school_id=str(u.school_id),
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        )
        for u in rows
    ]


@router.post("/teachers", response_model=TeacherOut, status_code=201)
async def create_teacher(
    payload: TeacherCreate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> TeacherOut:
    school_id = _require_school(admin)

    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=uuid4(),
        school_id=school_id,
        email=payload.email,
        full_name=payload.full_name,
        role=UserRole.teacher,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TeacherOut(
        id=str(user.id),
        school_id=str(user.school_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/teachers/{teacher_id}", response_model=TeacherOut)
async def update_teacher(
    teacher_id: str,
    payload: TeacherUpdate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> TeacherOut:
    school_id = _require_school(admin)
    user = (
        await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
                User.role == UserRole.teacher,
            )
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Teacher not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return TeacherOut(
        id=str(user.id),
        school_id=str(user.school_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/teachers/{teacher_id}")
async def deactivate_teacher(
    teacher_id: str,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    school_id = _require_school(admin)
    user = (
        await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
                User.role == UserRole.teacher,
            )
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Teacher not found")

    user.is_active = False
    await db.commit()
    return {"ok": True, "message": "Teacher deactivated"}


# ── Learner Management ──────────────────────────────────────────────────────

@router.get("/learners", response_model=list[LearnerOut])
async def list_learners(
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
    class_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LearnerOut]:
    school_id = _require_school(admin)
    query = (
        select(Learner)
        .where(Learner.school_id == school_id, Learner.deleted_at.is_(None))
        .order_by(Learner.full_name)
    )
    if class_id:
        query = query.where(Learner.class_id == class_id)
    if search:
        query = query.where(Learner.full_name.ilike(f"%{search}%"))
    query = query.offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return [
        LearnerOut(
            id=str(l.id),
            school_id=str(l.school_id),
            class_id=str(l.class_id),
            full_name=l.full_name,
            admission_no=l.admission_no,
            gender=l.gender,
            deleted_at=l.deleted_at.isoformat() if l.deleted_at else None,
        )
        for l in rows
    ]


@router.post("/learners", response_model=LearnerOut, status_code=201)
async def create_learner(
    payload: LearnerCreate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LearnerOut:
    school_id = _require_school(admin)

    if payload.class_id:
        class_obj = (
            await db.execute(
                select(SchoolClass).where(
                    SchoolClass.id == payload.class_id,
                    SchoolClass.school_id == school_id,
                )
            )
        ).scalar_one_or_none()
        if not class_obj:
            raise HTTPException(status_code=400, detail="Class not found in your school")

    learner = Learner(
        id=uuid4(),
        school_id=school_id,
        class_id=payload.class_id,
        full_name=payload.full_name,
        admission_no=payload.admission_no,
        gender=payload.gender,
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    return LearnerOut(
        id=str(learner.id),
        school_id=str(learner.school_id),
        class_id=str(learner.class_id),
        full_name=learner.full_name,
        admission_no=learner.admission_no,
        gender=learner.gender,
        deleted_at=None,
    )


@router.post("/learners/bulk", response_model=list[LearnerOut])
async def bulk_create_learners(
    payload: LearnerBulkCreate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> list[LearnerOut]:
    school_id = _require_school(admin)

    class_obj = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == payload.class_id,
                SchoolClass.school_id == school_id,
            )
        )
    ).scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=400, detail="Class not found in your school")

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
        learner = Learner(
            id=uuid4(),
            school_id=school_id,
            class_id=payload.class_id,
            full_name=name.strip(),
            admission_no=adm,
        )
        db.add(learner)
        learners.append(learner)

    await db.commit()
    for l in learners:
        await db.refresh(l)
    return [
        LearnerOut(
            id=str(l.id),
            school_id=str(l.school_id),
            class_id=str(l.class_id),
            full_name=l.full_name,
            admission_no=l.admission_no,
            gender=l.gender,
            deleted_at=None,
        )
        for l in learners
    ]


@router.patch("/learners/{learner_id}", response_model=LearnerOut)
async def update_learner(
    learner_id: str,
    payload: LearnerUpdate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LearnerOut:
    school_id = _require_school(admin)
    learner = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    if payload.full_name is not None:
        learner.full_name = payload.full_name
    if payload.class_id is not None:
        learner.class_id = payload.class_id
    if payload.admission_no is not None:
        learner.admission_no = payload.admission_no
    if payload.gender is not None:
        learner.gender = payload.gender

    await db.commit()
    await db.refresh(learner)
    return LearnerOut(
        id=str(learner.id),
        school_id=str(learner.school_id),
        class_id=str(learner.class_id),
        full_name=learner.full_name,
        admission_no=learner.admission_no,
        gender=learner.gender,
        deleted_at=None,
    )


@router.delete("/learners/{learner_id}")
async def delete_learner(
    learner_id: str,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    school_id = _require_school(admin)
    learner = (
        await db.execute(
            select(Learner).where(
                Learner.id == learner_id,
                Learner.school_id == school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    learner.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "message": "Learner deleted"}


# ── Class Management ────────────────────────────────────────────────────────

@router.get("/classes", response_model=list[ClassOut])
async def list_classes(
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ClassOut]:
    school_id = _require_school(admin)
    query = (
        select(SchoolClass)
        .where(SchoolClass.school_id == school_id, SchoolClass.deleted_at.is_(None))
        .order_by(SchoolClass.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(query)).scalars().all()
    return [
        ClassOut(
            id=str(c.id),
            school_id=str(c.school_id),
            teacher_id=str(c.teacher_id),
            name=c.name,
            grade_level=c.grade_level,
            learning_area_codes=[],
            deleted_at=c.deleted_at.isoformat() if c.deleted_at else None,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in rows
    ]


@router.post("/classes", response_model=ClassOut, status_code=201)
async def create_class(
    payload: ClassCreate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ClassOut:
    school_id = _require_school(admin)

    teacher_id = payload.teacher_id or str(admin.id)
    teacher = (
        await db.execute(
            select(User).where(
                User.id == teacher_id,
                User.school_id == school_id,
            )
        )
    ).scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=400, detail="Teacher not found in your school")

    class_obj = SchoolClass(
        id=uuid4(),
        school_id=school_id,
        teacher_id=teacher_id,
        name=payload.name,
        grade_level=payload.grade_level,
    )
    db.add(class_obj)
    await db.commit()
    await db.refresh(class_obj)
    return ClassOut(
        id=str(class_obj.id),
        school_id=str(class_obj.school_id),
        teacher_id=str(class_obj.teacher_id),
        name=class_obj.name,
        grade_level=class_obj.grade_level,
        learning_area_codes=[],
        deleted_at=None,
        created_at=class_obj.created_at.isoformat(),
        updated_at=class_obj.updated_at.isoformat(),
    )


@router.patch("/classes/{class_id}", response_model=ClassOut)
async def update_class(
    class_id: str,
    payload: ClassUpdate,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ClassOut:
    school_id = _require_school(admin)
    class_obj = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == class_id,
                SchoolClass.school_id == school_id,
                SchoolClass.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if payload.name is not None:
        class_obj.name = payload.name
    if payload.grade_level is not None:
        class_obj.grade_level = payload.grade_level
    if payload.teacher_id is not None:
        teacher = (
            await db.execute(
                select(User).where(
                    User.id == payload.teacher_id,
                    User.school_id == school_id,
                )
            )
        ).scalar_one_or_none()
        if not teacher:
            raise HTTPException(status_code=400, detail="Teacher not found in your school")
        class_obj.teacher_id = payload.teacher_id

    await db.commit()
    await db.refresh(class_obj)
    return ClassOut(
        id=str(class_obj.id),
        school_id=str(class_obj.school_id),
        teacher_id=str(class_obj.teacher_id),
        name=class_obj.name,
        grade_level=class_obj.grade_level,
        learning_area_codes=[],
        deleted_at=None,
        created_at=class_obj.created_at.isoformat(),
        updated_at=class_obj.updated_at.isoformat(),
    )


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: str,
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    school_id = _require_school(admin)
    class_obj = (
        await db.execute(
            select(SchoolClass).where(
                SchoolClass.id == class_id,
                SchoolClass.school_id == school_id,
                SchoolClass.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    class_obj.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "message": "Class deleted"}


# ── School Stats ─────────────────────────────────────────────────────────────

@router.get("/stats", response_model=SchoolStats)
async def get_school_stats(
    admin: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
) -> SchoolStats:
    school_id = _require_school(admin)
    total_teachers = (
        await db.execute(
            select(func.count()).select_from(User).where(
                User.school_id == school_id,
                User.role == UserRole.teacher,
            )
        )
    ).scalar() or 0
    total_learners = (
        await db.execute(
            select(func.count()).select_from(Learner).where(
                Learner.school_id == school_id,
                Learner.deleted_at.is_(None),
            )
        )
    ).scalar() or 0
    total_classes = (
        await db.execute(
            select(func.count()).select_from(SchoolClass).where(
                SchoolClass.school_id == school_id,
                SchoolClass.deleted_at.is_(None),
            )
        )
    ).scalar() or 0
    return SchoolStats(
        total_teachers=total_teachers,
        total_learners=total_learners,
        total_classes=total_classes,
    )
