"""Auth request/response schemas."""
from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

_PASSWORD_MIN_LENGTH = 8
_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


def validate_password_strength(password: str) -> str:
    """Minimum policy: 8+ chars with at least one letter and one digit."""
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters long")
    if not _HAS_LETTER.search(password) or not _HAS_DIGIT.search(password):
        raise ValueError("Password must contain at least one letter and one digit")
    return password


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    school_code: str = Field(min_length=4, max_length=16)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)


class ChangeSchoolCodeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_school_code: str = Field(min_length=4, max_length=16)


class UserOut(BaseModel):
    id: UUID
    school_id: UUID
    email: EmailStr
    full_name: str
    role: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
