"""Schools router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.school import School


router = APIRouter()


@router.get("/me")
async def my_school(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
    school = (
        await db.execute(select(School).where(School.id == user.school_id))
    ).scalar_one_or_none()
    if school is None:
        raise HTTPException(status_code=404, detail="School not found")
    return {
        "id": str(school.id),
        "name": school.name,
        "code": school.code,
        "county": school.county,
        "level": school.level,
    }
