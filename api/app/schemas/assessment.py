"""Assessment + AI generation schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RubricLevel(BaseModel):
    level: int = Field(ge=1, le=4)
    label: str
    descriptor: str = ""
    color: str | None = None


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
    diagram_description: str | None = None
    diagram_type: str | None = None
    diagram_data: str | None = None


class GenerateAssessmentRequest(BaseModel):
    learning_area_code: str
    strand_code: str
    sub_strand_codes: list[str] = Field(min_length=1)
    grade_level: str
    teacher_prompt: str | None = None
    item_count: int = Field(default=5, ge=1, le=20)
    include_diagrams: bool = False


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


class AssessmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    strand_code: str | None = None
    sub_strand_codes: list[str] | None = None
    rubric: Rubric | None = None
    items: list[AssessmentItem] | None = None
    tags: list[str] | None = None
    is_favourite: bool | None = None


class AssessmentOut(AssessmentIn):
    id: UUID
    owner_id: UUID
    school_id: UUID
    created_at: str
    updated_at: str
    deleted_at: str | None = None
