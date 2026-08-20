"""Score batching endpoints (offline sync target)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.models.run import AssessmentRun
from app.models.score import Score
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult, ScoreIn
from app.services.scores import upsert_scores

router = APIRouter()


@router.post("/batch", response_model=ScoreBatchResult)
async def post_batch(
    payload: ScoreBatchIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> ScoreBatchResult:
    # School scoping is enforced via the runs the scores reference.
    # v1.x adds an explicit school-id check on each run_id.
    return await upsert_scores(db, user.school_id, payload)


@router.get("/outbox", response_model=list[ScoreIn])
async def get_outbox(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    run_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[ScoreIn]:
    """Server-side outbox for the client to poll when Background Sync is unavailable.

    Returns the latest server-side scores for runs the current user's school
    owns.  The client can diff these against its local IndexedDB to reconcile
    conflicts or pull server-wins.
    """
    stmt = (
        select(Score)
        .join(AssessmentRun, Score.run_id == AssessmentRun.id)
        .where(
            AssessmentRun.school_id == user.school_id,
        )
    )
    if run_id:
        stmt = stmt.where(Score.run_id == run_id)
    stmt = stmt.order_by(Score.updated_at.desc()).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()
    return [
        ScoreIn(
            id=s.id,
            run_id=s.run_id,
            learner_id=s.learner_id,
            item_id=s.item_id,
            level=s.level,
            note=s.note,
            updated_at=s.updated_at.isoformat(),
        )
        for s in rows
    ]
