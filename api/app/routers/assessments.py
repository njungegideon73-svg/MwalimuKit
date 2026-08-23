"""Assessment generation + CRUD + export."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_provider
from app.core.db import get_db
from app.core.deps import CurrentUser
from app.core.metrics import inc_business_counter
from app.core.rate_limit import rate_limit_generate
from app.models.prompt_history import PromptHistory
from app.schemas.assessment import (
    AssessmentIn,
    AssessmentOut,
    AssessmentUpdate,
    GenerateAssessmentRequest,
    GenerateAssessmentResponse,
)
from app.services.assessments import (
    create_assessment as svc_create,
)
from app.services.assessments import (
    duplicate_assessment as svc_duplicate,
)
from app.services.assessments import (
    get_assessment as svc_get,
)
from app.services.assessments import (
    get_assessment_or_404,
)
from app.services.assessments import (
    list_assessments as svc_list,
)
from app.services.assessments import (
    soft_delete as svc_soft_delete,
)
from app.services.assessments import (
    toggle_favourite as svc_toggle_favourite,
)
from app.services.assessments import (
    update_assessment as svc_update,
)
from app.utils.activity_logger import log_activity

router = APIRouter()


@router.post("/generate", response_model=GenerateAssessmentResponse)
async def generate(
    request: Request,
    req: GenerateAssessmentRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(rate_limit_generate),
) -> GenerateAssessmentResponse:
    provider = get_provider()
    result = await provider.generate_assessment(
        learning_area=req.learning_area_code,
        strand=req.strand_code,
        sub_strand=", ".join(req.sub_strand_codes),
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
        include_diagrams=req.include_diagrams,
    )

    history = PromptHistory(
        user_id=user.id,
        school_id=user.school_id,
        learning_area_code=req.learning_area_code,
        strand_code=req.strand_code,
        sub_strand_codes=req.sub_strand_codes,
        grade_level=req.grade_level,
        teacher_prompt=req.teacher_prompt,
        item_count=req.item_count,
        response_rubric=result.rubric.model_dump() if hasattr(result.rubric, "model_dump") else result.rubric,
        response_items=[i.model_dump() for i in result.items] if hasattr(result.items[0], "model_dump") else result.items,
        provider=result.provider,
        model=result.model,
    )
    db.add(history)
    await db.commit()

    inc_business_counter("assessments_generated_total")
    return GenerateAssessmentResponse(
        rubric=result.rubric,
        items=result.items,
        provider=result.provider,
        model=result.model,
    )


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[AssessmentOut]:
    return await svc_list(db, user.school_id)


@router.post("", response_model=AssessmentOut)
async def create(
    payload: AssessmentIn, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    result = await svc_create(db, payload, user.school_id, user.id)
    inc_business_counter("assessments_created_total")
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.created",
        details={"name": result.name, "learning_area_code": payload.learning_area_code},
    )
    return result


@router.get("/{assessment_id}", response_model=AssessmentOut)
async def get(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    return await svc_get(db, assessment_id, user.school_id)


@router.post("/{assessment_id}/duplicate", response_model=AssessmentOut)
async def duplicate(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> AssessmentOut:
    result = await svc_duplicate(db, assessment_id, user.school_id, user.id)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.duplicated",
        details={"name": result.name},
    )
    return result


@router.patch("/{assessment_id}", response_model=AssessmentOut)
async def update(
    assessment_id: UUID,
    payload: AssessmentUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AssessmentOut:
    result = await svc_update(db, assessment_id, user.school_id, payload)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.updated",
        details={"name": result.name},
    )
    return result


@router.post("/{assessment_id}/favourite", response_model=AssessmentOut)
async def toggle_favourite(
    assessment_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AssessmentOut:
    result = await svc_toggle_favourite(db, assessment_id, user.school_id)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.favourited",
        details={"name": result.name, "is_favourite": result.is_favourite},
    )
    return result


@router.delete("/{assessment_id}")
async def soft_delete(
    assessment_id: UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    a = await get_assessment_or_404(db, assessment_id, user.school_id)
    await log_activity(
        db,
        user_id=user.id,
        school_id=user.school_id,
        action="assessment.deleted",
        details={"name": a.name},
    )
    return await svc_soft_delete(db, assessment_id, user.school_id)


# Export endpoints moved to app.routers.jobs for async processing.
# Use POST /api/v1/jobs/assessments/{assessment_id}/export/pdf
# and GET /api/v1/jobs/{job_id}/download
