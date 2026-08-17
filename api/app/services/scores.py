"""Score batching with last-write-wins."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import AssessmentRun
from app.models.score import Score
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult, ScoreIn


async def upsert_scores(db: AsyncSession, school_id, batch: ScoreBatchIn) -> ScoreBatchResult:
    accepted = 0
    conflicts = 0
    rejected: list[dict] = []

    run_ids = {s.run_id for s in batch.scores}
    if run_ids:
        valid_runs = (
            await db.execute(
                select(AssessmentRun.id).where(
                    AssessmentRun.id.in_(run_ids),
                    AssessmentRun.school_id == school_id,
                )
            )
        ).scalars().all()
        valid_run_set = set(valid_runs)
    else:
        valid_run_set = set()

    for s in batch.scores:
        if s.run_id not in valid_run_set:
            rejected.append({"id": str(s.id), "reason": "Run not found or access denied"})
            continue
        try:
            updated_at = datetime.fromisoformat(s.updated_at.replace("Z", "+00:00"))

            # Check for conflict: does a newer version already exist?
            existing = (
                await db.execute(
                    select(Score).where(
                        Score.run_id == s.run_id,
                        Score.learner_id == s.learner_id,
                        Score.item_id == s.item_id,
                    )
                )
            ).scalar_one_or_none()

            if existing and existing.updated_at > updated_at:
                conflicts += 1
                # Server wins — skip this write
                accepted += 1
                continue

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
    return ScoreBatchResult(accepted=accepted, conflicts=conflicts, rejected=rejected)
