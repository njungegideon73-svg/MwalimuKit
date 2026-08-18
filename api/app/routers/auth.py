"""Auth router."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.rate_limit import rate_limit_login
from app.core.security import hash_password, verify_password
from app.models.school import School
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest, ChangeSchoolCodeRequest,
    LoginRequest, RefreshRequest, SignupRequest, TokenPair,
)
from app.services.auth import login as svc_login
from app.services.auth import refresh_tokens as svc_refresh
from app.services.auth import signup as svc_signup
from app.utils.activity_logger import log_activity


router = APIRouter()


@router.post("/signup", response_model=TokenPair)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await svc_signup(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_login),
) -> TokenPair:
    try:
        result = await svc_login(db, email=payload.email, password=payload.password)
        user = (
            await db.execute(select(User).where(User.email == payload.email))
        ).scalar_one_or_none()
        if user:
            await log_activity(
                db,
                user_id=user.id,
                school_id=user.school_id,
                action="auth.login",
                details={"email": user.email},
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        return await svc_refresh(db, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from None


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"changed": True}


@router.post("/change-school-code")
async def change_school_code(
    payload: ChangeSchoolCodeRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect")

    school = (
        await db.execute(select(School).where(School.code == payload.new_school_code))
    ).scalar_one_or_none()
    if school is None:
        raise HTTPException(status_code=400, detail="School code not found")

    user.school_id = school.id
    await db.commit()
    return {"changed": True, "school_id": str(school.id)}
