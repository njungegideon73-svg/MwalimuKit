"""Auth request/response schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    school_code: str = Field(min_length=4, max_length=16)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


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
