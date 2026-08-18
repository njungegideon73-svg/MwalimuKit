"""Activity logging utilities."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog


async def log_activity(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    school_id: UUID | None,
    action: str,
    details: dict | None = None,
) -> None:
    stmt = insert(ActivityLog).values(
        user_id=user_id,
        school_id=school_id,
        action=action,
        details=details,
    )
    await db.execute(stmt)
    await db.commit()
