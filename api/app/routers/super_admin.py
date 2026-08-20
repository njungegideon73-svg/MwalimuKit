"""Super admin router - Full system management."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import SuperAdminUser
from app.core.security import hash_password
from app.models.activity_log import ActivityLog
from app.models.learner import Learner
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.user import User, UserRole
from app.schemas.classes import ActivityLogOut, LearnerOut
from app.utils.activity_logger import log_activity


router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class SchoolIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=4, max_length=16)
    county: str | None = None
    level: str | None = None


class SchoolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    code: str | None = Field(default=None, min_length=4, max_length=16)
    county: str | None = None
    level: str | None = None


class SchoolOut(BaseModel):
    id: str
    name: str
    code: str
    county: str | None
    level: str | None
    created_at: str


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="teacher")
    school_id: str | None = None
    school_code: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = None
    is_active: bool | None = None
    school_id: str | None = None


class UserOut(BaseModel):
    id: str
    school_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class LearnerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    school_id: str
    class_id: str | None = None
    admission_no: str | None = None
    gender: str | None = None


class LearnerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    school_id: str | None = None
    class_id: str | None = None
    admission_no: str | None = None
    gender: str | None = None


class SystemStats(BaseModel):
    total_schools: int
    total_users: int
    total_teachers: int
    total_school_admins: int
    total_super_admins: int
    total_learners: int
    total_classes: int


class FeatureFlagUpdate(BaseModel):
    key: str
    value: bool | int | str


class DashboardOut(BaseModel):
    total_schools: int
    total_users: int
    total_teachers: int
    total_school_admins: int
    total_super_admins: int
    total_learners: int
    total_classes: int
    recent_activities: list[ActivityLogOut]


# ── School Management ────────────────────────────────────────────────────────

@router.get("/schools", response_model=list[SchoolOut])
async def list_schools(
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SchoolOut]:
    query = select(School).order_by(School.created_at.desc())
    if search:
        query = query.where(
            School.name.ilike(f"%{search}%") | School.code.ilike(f"%{search}%")
        )
    query = query.offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return [
        SchoolOut(
            id=str(s.id),
            name=s.name,
            code=s.code,
            county=s.county,
            level=s.level,
            created_at=s.created_at.isoformat(),
        )
        for s in rows
    ]


@router.post("/schools", response_model=SchoolOut, status_code=201)
async def create_school(
    payload: SchoolIn,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> SchoolOut:
    existing = (
        await db.execute(select(School).where(School.code == payload.code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="School code already exists")

    school = School(
        id=uuid4(),
        name=payload.name,
        code=payload.code,
        county=payload.county,
        level=payload.level,
    )
    db.add(school)
    await db.commit()
    await db.refresh(school)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=school.id,
        action="school.created",
        details={"name": school.name, "code": school.code},
    )
    return SchoolOut(
        id=str(school.id),
        name=school.name,
        code=school.code,
        county=school.county,
        level=school.level,
        created_at=school.created_at.isoformat(),
    )


@router.patch("/schools/{school_id}", response_model=SchoolOut)
async def update_school(
    school_id: str,
    payload: SchoolUpdate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> SchoolOut:
    school = (
        await db.execute(select(School).where(School.id == school_id))
    ).scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    if payload.code and payload.code != school.code:
        existing = (
            await db.execute(select(School).where(School.code == payload.code))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="School code already exists")
        school.code = payload.code

    if payload.name is not None:
        school.name = payload.name
    if payload.county is not None:
        school.county = payload.county
    if payload.level is not None:
        school.level = payload.level

    await db.commit()
    await db.refresh(school)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=school.id,
        action="school.updated",
        details={"name": school.name, "code": school.code},
    )
    return SchoolOut(
        id=str(school.id),
        name=school.name,
        code=school.code,
        county=school.county,
        level=school.level,
        created_at=school.created_at.isoformat(),
    )


@router.delete("/schools/{school_id}")
async def delete_school(
    school_id: str,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    school = (
        await db.execute(select(School).where(School.id == school_id))
    ).scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    user_count = (
        await db.execute(
            select(func.count()).select_from(User).where(User.school_id == school_id)
        )
    ).scalar() or 0
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete school with {user_count} users. Remove users first.",
        )

    await db.delete(school)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=school.id,
        action="school.deleted",
        details={"name": school.name, "code": school.code},
    )
    await db.commit()
    return {"ok": True, "message": "School deleted"}


# ── User Management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserOut])
async def list_users(
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    school_id: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[UserOut]:
    query = select(User).order_by(User.created_at.desc())
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    if role:
        query = query.where(User.role == role)
    if school_id:
        query = query.where(User.school_id == school_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return [
        UserOut(
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


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    school_id = None
    if payload.school_id:
        school_id = payload.school_id
    elif payload.school_code:
        school = (
            await db.execute(select(School).where(School.code == payload.school_code))
        ).scalar_one_or_none()
        if not school:
            raise HTTPException(status_code=400, detail="School code not found")
        school_id = str(school.id)
    else:
        raise HTTPException(status_code=400, detail="Either school_id or school_code is required")

    try:
        role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {payload.role}")

    user = User(
        id=uuid4(),
        school_id=school_id,
        email=payload.email,
        full_name=payload.full_name,
        role=role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=user.school_id,
        action="user.created",
        details={"email": user.email, "role": str(user.role.value if hasattr(user.role, "value") else user.role)},
    )
    return UserOut(
        id=str(user.id),
        school_id=str(user.school_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        try:
            user.role = UserRole(payload.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {payload.role}")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.school_id is not None:
        user.school_id = payload.school_id

    await db.commit()
    await db.refresh(user)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=user.school_id,
        action="user.updated",
        details={"email": user.email, "role": str(user.role.value if hasattr(user.role, "value") else user.role)},
    )
    return UserOut(
        id=str(user.id),
        school_id=str(user.school_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    await log_activity(
        db,
        user_id=admin.id,
        school_id=user.school_id,
        action="user.deactivated",
        details={"email": user.email},
    )
    await db.commit()
    return {"ok": True, "message": "User deactivated"}


# ── Learner Management ──────────────────────────────────────────────────────

@router.get("/learners", response_model=list[LearnerOut])
async def list_all_learners(
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
    school_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LearnerOut]:
    query = select(Learner).where(Learner.deleted_at.is_(None)).order_by(Learner.full_name)
    if school_id:
        query = query.where(Learner.school_id == school_id)
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
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LearnerOut:
    school = (
        await db.execute(select(School).where(School.id == payload.school_id))
    ).scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=400, detail="School not found")

    if payload.class_id:
        class_obj = (
            await db.execute(select(SchoolClass).where(SchoolClass.id == payload.class_id))
        ).scalar_one_or_none()
        if not class_obj:
            raise HTTPException(status_code=400, detail="Class not found")

    learner = Learner(
        id=uuid4(),
        school_id=payload.school_id,
        class_id=payload.class_id,
        full_name=payload.full_name,
        admission_no=payload.admission_no,
        gender=payload.gender,
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=learner.school_id,
        action="learner.created",
        details={"full_name": learner.full_name, "class_id": str(learner.class_id)},
    )
    return LearnerOut(
        id=str(learner.id),
        school_id=str(learner.school_id),
        class_id=str(learner.class_id),
        full_name=learner.full_name,
        admission_no=learner.admission_no,
        gender=learner.gender,
        deleted_at=None,
    )


@router.patch("/learners/{learner_id}", response_model=LearnerOut)
async def update_learner(
    learner_id: str,
    payload: LearnerUpdate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LearnerOut:
    learner = (
        await db.execute(select(Learner).where(Learner.id == learner_id, Learner.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    if payload.full_name is not None:
        learner.full_name = payload.full_name
    if payload.school_id is not None:
        learner.school_id = payload.school_id
    if payload.class_id is not None:
        learner.class_id = payload.class_id
    if payload.admission_no is not None:
        learner.admission_no = payload.admission_no
    if payload.gender is not None:
        learner.gender = payload.gender

    await db.commit()
    await db.refresh(learner)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=learner.school_id,
        action="learner.updated",
        details={"full_name": learner.full_name, "class_id": str(learner.class_id)},
    )
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
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    learner = (
        await db.execute(select(Learner).where(Learner.id == learner_id, Learner.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    learner.deleted_at = datetime.now(timezone.utc)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=learner.school_id,
        action="learner.deleted",
        details={"full_name": learner.full_name},
    )
    await db.commit()
    return {"ok": True, "message": "Learner deleted"}


# ── System Statistics ────────────────────────────────────────────────────────

@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> SystemStats:
    total_schools = (await db.execute(select(func.count()).select_from(School))).scalar() or 0
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_teachers = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.teacher.value))
    ).scalar() or 0
    total_school_admins = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.school_admin.value))
    ).scalar() or 0
    total_super_admins = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.super_admin.value))
    ).scalar() or 0
    total_learners = (
        await db.execute(select(func.count()).select_from(Learner).where(Learner.deleted_at.is_(None)))
    ).scalar() or 0
    total_classes = (
        await db.execute(select(func.count()).select_from(SchoolClass).where(SchoolClass.deleted_at.is_(None)))
    ).scalar() or 0

    return SystemStats(
        total_schools=total_schools,
        total_users=total_users,
        total_teachers=total_teachers,
        total_school_admins=total_school_admins,
        total_super_admins=total_super_admins,
        total_learners=total_learners,
        total_classes=total_classes,
    )


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> DashboardOut:
    total_schools = (await db.execute(select(func.count()).select_from(School))).scalar() or 0
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_teachers = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.teacher.value))
    ).scalar() or 0
    total_school_admins = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.school_admin.value))
    ).scalar() or 0
    total_super_admins = (
        await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.super_admin.value))
    ).scalar() or 0
    total_learners = (
        await db.execute(select(func.count()).select_from(Learner).where(Learner.deleted_at.is_(None)))
    ).scalar() or 0
    total_classes = (
        await db.execute(select(func.count()).select_from(SchoolClass).where(SchoolClass.deleted_at.is_(None)))
    ).scalar() or 0

    recent_activities = (
        await db.execute(
            select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
        )
    ).scalars().all()

    return DashboardOut(
        total_schools=total_schools,
        total_users=total_users,
        total_teachers=total_teachers,
        total_school_admins=total_school_admins,
        total_super_admins=total_super_admins,
        total_learners=total_learners,
        total_classes=total_classes,
        recent_activities=[
            ActivityLogOut(
                id=a.id,
                user_id=a.user_id,
                school_id=a.school_id,
                action=a.action,
                details=a.details,
                created_at=a.created_at.isoformat(),
            )
            for a in recent_activities
        ],
    )


@router.get("/activities", response_model=list[ActivityLogOut])
async def list_activities(
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
    school_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ActivityLogOut]:
    query = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if school_id:
        query = query.where(ActivityLog.school_id == school_id)
    if user_id:
        query = query.where(ActivityLog.user_id == user_id)
    if action:
        query = query.where(ActivityLog.action == action)
    if search:
        query = query.where(ActivityLog.action.ilike(f"%{search}%") | ActivityLog.details.astext.ilike(f"%{search}%"))
    query = query.offset(offset).limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return [
        ActivityLogOut(
            id=a.id,
            user_id=a.user_id,
            school_id=a.school_id,
            action=a.action,
            details=a.details,
            created_at=a.created_at.isoformat(),
        )
        for a in rows
    ]
