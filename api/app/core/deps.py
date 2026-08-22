"""Common FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc from None

    user = (
        await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    ).scalar_one_or_none()
    if user is None:
        raise credentials_exc

    # Session invalidation: reload user to get fresh token_version from database.
    # This ensures that password changes or session revocations are recognized
    # even if the user object was cached in the session.
    refreshed_user = await db.get(User, user.id)
    if refreshed_user is None:
        raise credentials_exc

    # Tokens issued before the current token_version (e.g. pre-password-change)
    # are rejected. Missing `ver` claim is only accepted while the user is
    # still at version 0.
    if payload.get("ver", 0) != refreshed_user.token_version:
        raise credentials_exc
    return refreshed_user


def require_role(*allowed_roles: UserRole):
    """Dependency factory that checks if the current user has one of the allowed roles."""
    async def _check_role(user: CurrentUser) -> User:
        user_role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(r.value for r in allowed_roles)}",
            )
        return user
    return _check_role


async def require_super_admin(user: CurrentUser) -> User:
    """Dependency that requires super_admin role."""
    user_role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    if user_role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required.",
        )
    return user


async def require_school_admin_or_above(user: CurrentUser) -> User:
    """Dependency that requires school_admin or super_admin role."""
    user_role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    if user_role not in (UserRole.school_admin, UserRole.super_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. School admin or super admin role required.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
SchoolAdminUser = Annotated[User, Depends(require_school_admin_or_above)]
