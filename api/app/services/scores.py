"""Score batching with last-write-wins + conflict reporting."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import AssessmentRun
from app.models.score import Score
from app.schemas.run_score import ScoreBatchIn, ScoreBatchResult


async def upsert_scores(db: AsyncSession, school_id, batch: ScoreBatchIn) -> ScoreBatchResult:
    accepted = 0
    conflicts = 0
    rejected: list[dict] = []
    conflicted_rows: list[dict] = []

    run_ids = {s.run_id for s in batch.scores}
    valid_run_set = set()
    run_school_map: dict = {}
    if run_ids:
        valid_runs = (
            await db.execute(
                select(AssessmentRun.id, AssessmentRun.school_id).where(
                    AssessmentRun.id.in_(run_ids),
                    AssessmentRun.school_id == school_id,
                )
            )
        ).all()
        valid_run_set = {r.id for r in valid_runs}
        run_school_map = {r.id: r.school_id for r in valid_runs}

    for s in batch.scores:
        if s.run_id not in valid_run_set:
            rejected.append({"id": str(s.id), "reason": "Run not found or access denied"})
            continue
        try:
            updated_at = datetime.fromisoformat(s.updated_at.replace("Z", "+00:00")).replace(tzinfo=None)

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
                accepted += 1
                conflicted_rows.append({
                    "id": str(s.id),
                    "learner_id": str(s.learner_id),
                    "item_id": s.item_id,
                    "server_level": existing.level,
                    "client_level": s.level,
                    "server_updated_at": existing.updated_at.isoformat(),
                })
                continue

            score_school_id = run_school_map.get(s.run_id, school_id)
            if existing:
                existing.level = s.level
                existing.note = s.note
                existing.updated_at = updated_at
                existing.school_id = score_school_id
                await db.merge(existing)
            else:
                score = Score(
                    id=s.id,
                    run_id=s.run_id,
                    learner_id=s.learner_id,
                    school_id=score_school_id,
                    item_id=s.item_id,
                    level=s.level,
                    note=s.note,
                    updated_at=updated_at,
                )
                db.add(score)
            accepted += 1
        except Exception as exc:  # noqa: BLE001
            rejected.append({"id": str(s.id), "reason": str(exc)})

    await db.commit()
    return ScoreBatchResult(
        accepted=accepted,
        conflicts=conflicts,
        rejected=rejected,
        conflicted_rows=conflicted_rows,
    )
