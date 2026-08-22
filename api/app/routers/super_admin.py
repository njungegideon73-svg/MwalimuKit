"""Super admin router - Full system management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import SuperAdminUser
from app.core.metrics import inc_business_counter
from app.models.activity_log import ActivityLog
from app.models.learner import Learner
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.user import User, UserRole
from app.schemas.auth import validate_password_strength
from app.schemas.classes import ActivityLogOut, LearnerOut
from app.services import admin as admin_service
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

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)


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
    search: str | None = Query(default=None, max_length=100),
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
    try:
        school = await admin_service.create_school(
            db, name=payload.name, code=payload.code, county=payload.county, level=payload.level
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

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
    school = await admin_service.get_school(db, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    try:
        if payload.code and payload.code != school.code:
            await admin_service.ensure_school_code_available(
                db, payload.code, exclude_school_id=school.id
            )
            school.code = payload.code
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

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
    school = await admin_service.get_school(db, school_id)
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
    search: str | None = Query(default=None, max_length=100),
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
    return [UserOut(**admin_service.serialize_user(u)) for u in rows]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    school_id = payload.school_id
    if not school_id:
        if not payload.school_code:
            raise HTTPException(status_code=400, detail="Either school_id or school_code is required")
        school = (
            await db.execute(select(School).where(School.code == payload.school_code))
        ).scalar_one_or_none()
        if not school:
            raise HTTPException(status_code=400, detail="School code not found")
        school_id = str(school.id)

    try:
        role = admin_service.parse_role(payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        user = await admin_service.create_user(
            db,
            school_id=school_id,
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
            role=role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await log_activity(
        db,
        user_id=admin.id,
        school_id=user.school_id,
        action="user.created",
        details={"email": user.email, "role": admin_service.user_role_str(user)},
    )
    return UserOut(**admin_service.serialize_user(user))


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await admin_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        try:
            user.role = admin_service.parse_role(payload.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
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
        details={"email": user.email, "role": admin_service.user_role_str(user)},
    )
    return UserOut(**admin_service.serialize_user(user))


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await admin_service.get_user(db, user_id)
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
    search: str | None = Query(default=None, max_length=100),
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
    return [LearnerOut(**admin_service.serialize_learner(l)) for l in rows]


@router.post("/learners", response_model=LearnerOut, status_code=201)
async def create_learner(
    payload: LearnerCreate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LearnerOut:
    school = await admin_service.get_school(db, payload.school_id)
    if not school:
        raise HTTPException(status_code=400, detail="School not found")

    try:
        learner = await admin_service.create_learner(
            db,
            school_id=payload.school_id,
            class_id=payload.class_id,
            full_name=payload.full_name,
            admission_no=payload.admission_no,
            gender=payload.gender,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    await log_activity(
        db,
        user_id=admin.id,
        school_id=learner.school_id,
        action="learner.created",
        details={"full_name": learner.full_name, "class_id": str(learner.class_id)},
    )
    return LearnerOut(**admin_service.serialize_learner(learner))


@router.patch("/learners/{learner_id}", response_model=LearnerOut)
async def update_learner(
    learner_id: str,
    payload: LearnerUpdate,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> LearnerOut:
    learner = await admin_service.get_active_learner(db, learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    await admin_service.update_learner(
        db,
        learner,
        school_id=payload.school_id,
        class_id=payload.class_id,
        full_name=payload.full_name,
        admission_no=payload.admission_no,
        gender=payload.gender,
    )
    await log_activity(
        db,
        user_id=admin.id,
        school_id=learner.school_id,
        action="learner.updated",
        details={"full_name": learner.full_name, "class_id": str(learner.class_id)},
    )
    return LearnerOut(**admin_service.serialize_learner(learner))


@router.delete("/learners/{learner_id}")
async def delete_learner(
    learner_id: str,
    admin: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    learner = await admin_service.get_active_learner(db, learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")

    await admin_service.soft_delete_learner(db, learner)
    await log_activity(
        db,
        user_id=admin.id,
        school_id=learner.school_id,
        action="learner.deleted",
        details={"full_name": learner.full_name},
    )
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

    inc_business_counter("super_admin_dashboard_views_total")

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
    search: str | None = Query(default=None, max_length=100),
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
