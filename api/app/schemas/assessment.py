"""Assessment + AI generation schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RubricLevel(BaseModel):
    level: int = Field(ge=1, le=4)
    label: str
    descriptor: str = ""


class RubricCriterion(BaseModel):
    id: str
    label: str


class Rubric(BaseModel):
    levels: list[RubricLevel]
    criteria: list[RubricCriterion]


class AssessmentItem(BaseModel):
    id: str
    criterion: str
    stem: str
    answer_guide: str | None = None
    max_level: int = 4


class GenerateAssessmentRequest(BaseModel):
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str] = Field(min_length=1)
    grade_level: str
    teacher_prompt: str | None = None
    item_count: int = Field(default=5, ge=1, le=10)


class GenerateAssessmentResponse(BaseModel):
    rubric: Rubric
    items: list[AssessmentItem]
    provider: str
    model: str


class AssessmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str]
    source: str = "manual"
    rubric: Rubric
    items: list[AssessmentItem]
    tags: list[str] = Field(default_factory=list)
    is_favourite: bool = False


class AssessmentOut(AssessmentIn):
    id: UUID
    owner_id: UUID
    school_id: UUID
    created_at: str
    updated_at: str
    deleted_at: str | None = None
