"""Run + score schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RunIn(BaseModel):
    class_id: UUID
    assessment_id: UUID
    term: str | None = None


class RunOut(BaseModel):
    id: UUID
    school_id: UUID
    class_id: UUID
    assessment_id: UUID
    term: str | None
    started_at: str
    closed_at: str | None


class ScoreIn(BaseModel):
    id: UUID
    run_id: UUID
    learner_id: UUID
    item_id: str
    level: int | None = Field(default=None, ge=1, le=4)
    note: str | None = None
    updated_at: str


class ScoreBatchIn(BaseModel):
    scores: list[ScoreIn]


class ScoreBatchResult(BaseModel):
    accepted: int
    conflicts: int = 0
    rejected: list[dict]
    conflicted_rows: list[dict] = Field(default_factory=list)
