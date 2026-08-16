"""Score batching endpoints (offline sync target)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult
from app.services.scores import upsert_scores


router = APIRouter()


@router.post("/batch", response_model=ScoreBatchResult)
async def post_batch(
    payload: ScoreBatchIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> ScoreBatchResult:
    # School scoping is enforced via the runs the scores reference.
    # v1.x adds an explicit school-id check on each run_id.
    return await upsert_scores(db, user.school_id, payload)
