"""Shared pagination schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class PaginatedResponse(BaseModel):
    total: int
    offset: int
    limit: int
