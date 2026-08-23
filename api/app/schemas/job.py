"""Job schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobOut(BaseModel):
    id: UUID
    type: str
    status: str
    payload: dict
    result: dict | None
    error: str | None
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    id: UUID
    status: str
    result: dict | None
    error: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}
