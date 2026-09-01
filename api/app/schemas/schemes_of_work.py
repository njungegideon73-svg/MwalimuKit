"""Schemes of Work schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CalendarInterruptionIn(BaseModel):
    week_number: int = Field(ge=1)
    interruption_type: Literal["mid_term_break", "exam_week", "public_holiday", "school_activity", "other"]
    label: str


class SchemeOfWorkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sub_strand_code: str
    grade: str
    learning_area_code: str
    academic_year: str
    term_number: int = Field(ge=1, le=3)
    lessons_per_week: int = Field(ge=1, le=10, default=3)
    total_weeks: int = Field(ge=1, le=20, default=14)
    start_week: int = Field(ge=1, default=1)
    calendar_interruptions: list[CalendarInterruptionIn] = Field(default_factory=list)


class SchemeOfWorkOut(BaseModel):
    id: UUID
    name: str
    sub_strand_code: str
    grade: str
    learning_area_code: str
    academic_year: str
    term_number: int
    lessons_per_week: int
    total_weeks: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SchemeLessonOut(BaseModel):
    id: UUID
    scheme_id: UUID
    week_number: int
    lesson_number: int
    content_id: UUID | None
    is_break: bool
    break_label: str | None
    strand_code: str | None
    sub_strand_code: str | None
    topic: str | None
    learning_outcomes: list[str]
    learning_experiences: list[str]
    key_inquiry_questions: list[str]
    resources: list[str]
    assessment_methods: list[str]
    notes: str | None

    model_config = {"from_attributes": True}


class SchemeOfWorkDetail(BaseModel):
    scheme: SchemeOfWorkOut
    lessons: list[SchemeLessonOut]


class LessonContentIn(BaseModel):
    sub_strand_code: str
    term_number: int = Field(ge=1, le=3)
    sequence_order: int = Field(ge=0)
    topic: str
    learning_outcomes: list[str] = Field(default_factory=list)
    learning_experiences: list[str] = Field(default_factory=list)
    key_inquiry_questions: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    assessment_methods: list[str] = Field(default_factory=list)
    value_signs: list[str] | None = None
    core_competences: list[str] | None = None


class LessonContentOut(BaseModel):
    id: UUID
    sub_strand_code: str
    term_number: int
    sequence_order: int
    topic: str
    learning_outcomes: list[str]
    learning_experiences: list[str]
    key_inquiry_questions: list[str]
    resources: list[str]
    assessment_methods: list[str]
    value_signs: list[str] | None
    core_competences: list[str] | None

    model_config = {"from_attributes": True}


class SchemePreviewRequest(SchemeOfWorkCreate):
    pass


class SchemePreviewItem(BaseModel):
    week_number: int
    lesson_number: int
    lesson_sequence: int | None
    is_break: bool
    break_label: str | None
    strand_code: str | None
    sub_strand_code: str | None
    topic: str | None
    learning_outcomes: list[str] | None = None
    learning_experiences: list[str] | None = None
    key_inquiry_questions: list[str] | None = None
    resources: list[str] | None = None
    assessment_methods: list[str] | None = None
    notes: str | None = None


class SchemePreviewResponse(BaseModel):
    scheme: SchemeOfWorkOut
    lessons: list[SchemePreviewItem]