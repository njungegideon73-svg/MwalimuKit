"""Roadmap / feature request schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class FeatureRequestIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)


class FeatureRequestOut(BaseModel):
    id: UUID
    title: str
    description: str
    status: str
    vote_count: int
    created_by: str | None = None
    created_at: str
    user_has_voted: bool = False
