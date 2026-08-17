"""Auth business logic."""
from __future__ import annotations

from uuid import uuid4

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.models.school import School
from app.models.user import User, UserRole
from app.schemas.auth import SignupRequest, TokenPair, UserOut


async def signup(db: AsyncSession, payload: SignupRequest) -> TokenPair:
    school = (
        await db.execute(select(School).where(School.code == payload.school_code))
    ).scalar_one_or_none()
    if school is None:
        raise ValueError("School code not found. Ask your school admin for the join code.")

    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Email already registered. Try logging in.")

    user = User(
        id=uuid4(),
        school_id=school.id,
        email=payload.email,
        full_name=payload.full_name,
        role=UserRole.teacher,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _pair(user)


async def login(db: AsyncSession, *, email: str, password: str) -> TokenPair:
    user = (
        await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password.")
    return _pair(user)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:
        raise ValueError("Invalid or expired refresh token.") from exc

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type.")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload.")

    user = (
        await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None:
        raise ValueError("User not found or deactivated.")

    return _pair(user)


def _pair(user: User) -> TokenPair:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserOut(
            id=user.id,
            school_id=user.school_id,
            email=user.email,
            full_name=user.full_name,
            role=role,
        ),
    )
