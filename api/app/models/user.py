"""User model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class UserRole(str, PyEnum):
    teacher = "teacher"
    school_admin = "school_admin"
    super_admin = "super_admin"


class User(UUIDPK, Timestamped, Base):
    __tablename__ = "users"

    school_id: Mapped["__import__('uuid').UUID"] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.teacher,
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Bumped on password change / session revocation: JWTs carry `ver` and
    # are rejected when it no longer matches (see core/deps.get_current_user).
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
