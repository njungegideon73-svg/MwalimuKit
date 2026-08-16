"""Score batching with last-write-wins."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score import Score
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult, ScoreIn


async def upsert_scores(db: AsyncSession, school_id, batch: ScoreBatchIn) -> ScoreBatchResult:
    accepted = 0
    rejected: list[dict] = []

    for s in batch.scores:
        try:
            updated_at = datetime.fromisoformat(s.updated_at.replace("Z", "+00:00"))
            stmt = (
                pg_insert(Score)
                .values(
                    id=s.id,
                    run_id=s.run_id,
                    learner_id=s.learner_id,
                    item_id=s.item_id,
                    level=s.level,
                    note=s.note,
                    updated_at=updated_at,
                )
                .on_conflict_do_update(
                    index_elements=["run_id", "learner_id", "item_id"],
                    set_={"level": s.level, "note": s.note, "updated_at": updated_at},
                )
            )
            await db.execute(stmt)
            accepted += 1
        except Exception as exc:  # noqa: BLE001
            rejected.append({"id": str(s.id), "reason": str(exc)})

    await db.commit()
    return ScoreBatchResult(accepted=accepted, rejected=rejected)
