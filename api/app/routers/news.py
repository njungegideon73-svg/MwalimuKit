"""News items – admin posts, all users read."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, SuperAdminUser
from app.models.news_item import NewsItem
from app.models.user import UserRole
from app.schemas.news import NewsItemIn, NewsItemOut

router = APIRouter()


@router.get("", response_model=list[NewsItemOut])
async def list_news(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[NewsItemOut]:
    user_role = user.role if hasattr(user.role, "value") else str(user.role)
    if user_role in (UserRole.super_admin.value,):
        stmt = select(NewsItem).where(NewsItem.is_active.is_(True)).order_by(NewsItem.created_at.desc())
    else:
        stmt = (
            select(NewsItem)
            .where(NewsItem.is_active.is_(True), NewsItem.school_id == user.school_id)
            .order_by(NewsItem.created_at.desc())
        )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        NewsItemOut(
            id=str(n.id),
            title=n.title,
            content=n.content,
            category=n.category,
            is_active=n.is_active,
            school_id=str(n.school_id) if n.school_id else None,
            created_by=str(n.created_by),
            created_at=n.created_at.isoformat(),
        )
        for n in rows
    ]


@router.post("", response_model=NewsItemOut)
async def create_news(
    payload: NewsItemIn,
    user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> NewsItemOut:
    from uuid import UUID
    school_id = UUID(payload.school_id) if payload.school_id else user.school_id
    n = NewsItem(
        id=uuid4(),
        title=payload.title,
        content=payload.content,
        category=payload.category,
        is_active=payload.is_active,
        created_by=user.id,
        school_id=school_id,
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return NewsItemOut(
        id=str(n.id),
        title=n.title,
        content=n.content,
        category=n.category,
        is_active=n.is_active,
        school_id=str(n.school_id) if n.school_id else None,
        created_by=str(n.created_by),
        created_at=n.created_at.isoformat(),
    )


@router.delete("/{news_id}")
async def delete_news(
    news_id: str,
    user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from uuid import UUID

    n = (
        await db.execute(
            select(NewsItem).where(NewsItem.id == UUID(news_id))
        )
    ).scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=404, detail="News item not found")
    n.is_active = False
    await db.commit()
    return {"ok": True}
