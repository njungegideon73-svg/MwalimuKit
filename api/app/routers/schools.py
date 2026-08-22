"""Schools router."""
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.school import School

logger = structlog.get_logger()

router = APIRouter()


@router.get("/me")
async def my_school(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    logger.warning("schools_me_called", uid=str(user.id), school_id=str(user.school_id))
    school = (
        await db.execute(select(School).where(School.id == user.school_id))
    ).scalar_one_or_none()
    if school is None:
        logger.warning("school_not_found", uid=str(user.id), school_id=str(user.school_id))
        raise HTTPException(status_code=404, detail="School not found")
    return {
        "id": str(school.id),
        "name": school.name,
        "code": school.code,
        "county": school.county,
        "level": school.level,
    }
