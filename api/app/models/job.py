"""Background job model."""
from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, LargeBinary, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base, Timestamped


class JobType(str, PyEnum):
    assessment_pdf = "assessment_pdf"
    assessment_docx = "assessment_docx"
    report_card_pdf = "report_card_pdf"
    sba_report_card_pdf = "sba_report_card_pdf"
    class_summary_csv = "class_summary_csv"
    term_exam_class_csv = "term_exam_class_csv"


class JobStatus(str, PyEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Job(UUIDPK, Timestamped, Base):
    __tablename__ = "jobs"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    school_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("schools.id"), nullable=False)
    type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type", native_enum=False), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False),
        nullable=False,
        default=JobStatus.pending,
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
