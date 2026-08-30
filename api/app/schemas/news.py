"""News item schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class NewsItemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="news", max_length=50)
    is_active: bool = Field(default=True)
    school_id: str | None = None


class NewsItemOut(BaseModel):
    id: str
    title: str
    content: str
    category: str
    is_active: bool
    school_id: str | None = None
    created_by: str
    created_at: str
