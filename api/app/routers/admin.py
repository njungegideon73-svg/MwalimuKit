"""School admin dashboard + public roadmap endpoints."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.assessment import Assessment
from app.models.feature_request import FeatureRequest
from app.models.feature_vote import FeatureVote
from app.models.learner import Learner
from app.models.run import AssessmentRun
from app.models.school_class import SchoolClass
from app.models.score import Score
from app.schemas.roadmap import FeatureRequestIn, FeatureRequestOut


router = APIRouter()


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def admin_dashboard(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict:
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
