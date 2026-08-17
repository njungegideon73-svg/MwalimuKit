"""Class + learner schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade_level: str = Field(min_length=1, max_length=16)
    learning_area_codes: list[str] = Field(default_factory=list)


class ClassOut(ClassIn):
    id: UUID
    school_id: UUID
    teacher_id: UUID
    deleted_at: str | None = None
    created_at: str
    updated_at: str


class LearnerIn(BaseModel):
    class_id: UUID
    full_name: str = Field(min_length=1, max_length=120)
    admission_no: str | None = None
    gender: str | None = None


class LearnerBulkIn(BaseModel):
    class_id: UUID
    lines: list[str] = Field(min_length=1)


class LearnerUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    admission_no: str | None = None
    gender: str | None = None


class LearnerOut(BaseModel):
    id: UUID
    school_id: UUID
    class_id: UUID
    full_name: str
    admission_no: str | None
    gender: str | None
    deleted_at: str | None


class LearnerWithClassName(BaseModel):
    id: UUID
    school_id: UUID
    class_id: UUID
    full_name: str
    admission_no: str | None
    gender: str | None
    deleted_at: str | None
    class_name: str
