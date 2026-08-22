"""School admin dashboard + public roadmap + activity log endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, SchoolAdminUser
from app.core.metrics import inc_business_counter
from app.models.activity_log import ActivityLog
from app.models.assessment import Assessment
from app.models.feature_request import FeatureRequest
from app.models.feature_vote import FeatureVote
from app.models.learner import Learner
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass
from app.models.score import Score
from app.schemas.classes import ActivityLogOut
from app.schemas.roadmap import FeatureRequestIn, FeatureRequestOut


router = APIRouter()


class ActivityLogPage(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[ActivityLogOut]


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def admin_dashboard(user: SchoolAdminUser, db: AsyncSession = Depends(get_db)) -> dict:
    school_filter = lambda T: T.school_id == user.school_id  # noqa: E731

    total_learners = (
        await db.execute(
            select(func.count()).select_from(Learner).where(
                school_filter(Learner), Learner.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    total_classes = (
        await db.execute(
            select(func.count()).select_from(SchoolClass).where(
                school_filter(SchoolClass), SchoolClass.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    total_assessments = (
        await db.execute(
            select(func.count()).select_from(Assessment).where(
                school_filter(Assessment), Assessment.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    total_runs = (
        await db.execute(
            select(func.count()).select_from(AssessmentRun).where(
                school_filter(AssessmentRun)
            )
        )
    ).scalar() or 0

    total_scores = (
        await db.execute(
            select(func.count()).select_from(Score)
            .join(AssessmentRun, Score.run_id == AssessmentRun.id)
            .where(school_filter(AssessmentRun))
        )
    ).scalar() or 0

    inc_business_counter("dashboard_views_total", {"role": "school_admin"})

    recent_assessments_rows = (
        await db.execute(
            select(Assessment)
            .where(school_filter(Assessment), Assessment.deleted_at.is_(None))
            .order_by(Assessment.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    recent_assessments = [
        {"id": str(a.id), "name": a.name, "created_at": a.created_at.isoformat()}
        for a in recent_assessments_rows
    ]

    recent_runs_rows = (
        await db.execute(
            select(AssessmentRun, SchoolClass.name.label("class_name"), Assessment.name.label("assessment_name"))
            .join(SchoolClass, AssessmentRun.class_id == SchoolClass.id)
            .join(Assessment, AssessmentRun.assessment_id == Assessment.id)
            .where(school_filter(AssessmentRun))
            .order_by(AssessmentRun.started_at.desc())
            .limit(5)
        )
    ).all()
    recent_runs = [
        {
            "id": str(row[0].id),
            "class_name": row[1],
            "assessment_name": row[2],
            "started_at": row[0].started_at.isoformat(),
        }
        for row in recent_runs_rows
    ]

    return {
        "total_learners": total_learners,
        "total_classes": total_classes,
        "total_assessments": total_assessments,
        "total_runs": total_runs,
        "total_scores": total_scores,
        "recent_assessments": recent_assessments,
        "recent_runs": recent_runs,
    }


# ── Activity Log ─────────────────────────────────────────────────────────────

@router.get("/activity-log", response_model=ActivityLogPage)
async def query_activity_log(
    user: SchoolAdminUser,
    db: AsyncSession = Depends(get_db),
    school_id: str | None = Query(default=None, description="Super admins only; defaults to caller's school"),
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None, description="Exact match, e.g. 'auth.login'"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> ActivityLogPage:
    """Paginated audit trail. School admins see their own school; super admins
    may pass `school_id` to inspect any school (omit for all schools)."""
    is_super = user.role.value if hasattr(user.role, "value") else str(user.role)
    effective_school_id: UUID | None = user.school_id
    if school_id:
        if is_super != "super_admin":
            raise HTTPException(status_code=403, detail="Only super admins can query other schools")
        effective_school_id = UUID(school_id)
    elif is_super == "super_admin":
        effective_school_id = None  # super admin without explicit filter sees everything

    filters = [ActivityLog.created_at >= date_from if date_from else None,
               ActivityLog.created_at <= date_to if date_to else None,
               ActivityLog.school_id == effective_school_id if effective_school_id else None,
               ActivityLog.user_id == user_id if user_id else None,
               ActivityLog.action == action if action else None]
    filters = [f for f in filters if f is not None]

    base = select(ActivityLog).where(*filters)
    total = (
        await db.execute(select(func.count()).select_from(ActivityLog).where(*filters))
    ).scalar() or 0
    rows = (
        await db.execute(base.order_by(ActivityLog.created_at.desc()).offset(offset).limit(limit))
    ).scalars().all()

    return ActivityLogPage(
        total=total,
        offset=offset,
        limit=limit,
        items=[
            ActivityLogOut(
                id=a.id,
                user_id=a.user_id,
                school_id=a.school_id,
                action=a.action,
                details=a.details,
                created_at=a.created_at.isoformat(),
            )
            for a in rows
        ],
    )


# ── Roadmap ──────────────────────────────────────────────────────────────────

@router.get("/roadmap")
async def list_roadmap(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[FeatureRequestOut]:
    rows = (
        await db.execute(
            select(FeatureRequest).order_by(FeatureRequest.vote_count.desc())
        )
    ).scalars().all()

    user_vote_ids: set[UUID] = set()
    votes = (
        await db.execute(
            select(FeatureVote.feature_id).where(FeatureVote.user_id == user.id)
        )
    ).scalars().all()
    user_vote_ids = set(votes)

    return [
        FeatureRequestOut(
            id=f.id,
            title=f.title,
            description=f.description,
            status=f.status,
            vote_count=f.vote_count,
            created_at=f.created_at.isoformat(),
            user_has_voted=f.id in user_vote_ids,
        )
        for f in rows
    ]


@router.post("/roadmap", response_model=FeatureRequestOut)
async def create_feature_request(
    payload: FeatureRequestIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> FeatureRequestOut:
    fr = FeatureRequest(
        id=uuid4(),
        title=payload.title,
        description=payload.description,
    )
    db.add(fr)
    await db.commit()
    await db.refresh(fr)
    return FeatureRequestOut(
        id=fr.id,
        title=fr.title,
        description=fr.description,
        status=fr.status,
        vote_count=fr.vote_count,
        created_at=fr.created_at.isoformat(),
        user_has_voted=False,
    )


@router.post("/roadmap/{feature_id}/vote", response_model=FeatureRequestOut)
async def toggle_vote(
    feature_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> FeatureRequestOut:
    fr = (
        await db.execute(
            select(FeatureRequest).where(FeatureRequest.id == feature_id)
        )
    ).scalar_one_or_none()
    if fr is None:
        raise HTTPException(status_code=404, detail="Feature request not found")

    existing = (
        await db.execute(
            select(FeatureVote).where(
                FeatureVote.feature_id == feature_id,
                FeatureVote.user_id == user.id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        fr.vote_count -= 1
        user_has_voted = False
    else:
        vote = FeatureVote(id=uuid4(), feature_id=feature_id, user_id=user.id)
        db.add(vote)
        fr.vote_count += 1
        user_has_voted = True

    await db.commit()
    await db.refresh(fr)

    return FeatureRequestOut(
        id=fr.id,
        title=fr.title,
        description=fr.description,
        status=fr.status,
        vote_count=fr.vote_count,
        created_at=fr.created_at.isoformat(),
        user_has_voted=user_has_voted,
    )
