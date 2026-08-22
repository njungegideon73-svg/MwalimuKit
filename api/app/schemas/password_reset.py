"""Password reset request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import validate_password_strength


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordResponse(BaseModel):
    detail: str = "If the email exists, a reset link has been sent."
