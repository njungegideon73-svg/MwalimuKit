"""Add term_exams and learner_exam_scores tables for SBA.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "term_exams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("class_id", UUID(as_uuid=True), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("learning_area_id", UUID(as_uuid=True), sa.ForeignKey("learning_areas.id"), nullable=False),
        sa.Column("term", sa.Integer(), nullable=False),
        sa.Column("exam_type", sa.Text(), nullable=False),
        sa.Column("academic_year", sa.Text(), nullable=False),
        sa.Column("max_marks", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_term_exams_class", "term_exams", ["class_id"])
    op.create_index("ix_term_exams_school", "term_exams", ["school_id"])

    op.create_table(
        "learner_exam_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("term_exam_id", UUID(as_uuid=True), sa.ForeignKey("term_exams.id"), nullable=False),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("marks", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("term_exam_id", "learner_id", name="uq_learner_exam_score"),
    )
    op.create_index("ix_learner_exam_scores_learner", "learner_exam_scores", ["learner_id"])
    op.create_index("ix_learner_exam_scores_exam", "learner_exam_scores", ["term_exam_id"])


def downgrade() -> None:
    op.drop_table("learner_exam_scores")
    op.drop_table("term_exams")
