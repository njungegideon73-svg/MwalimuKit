"""Add jobs table for background export processing."""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE job_type AS ENUM (
            'assessment_pdf',
            'assessment_docx',
            'report_card_pdf',
            'sba_report_card_pdf',
            'class_summary_csv',
            'term_exam_class_csv'
        )
    """)
    op.execute("""
        CREATE TYPE job_status AS ENUM (
            'pending',
            'processing',
            'completed',
            'failed',
            'cancelled'
        )
    """)
    op.create_table(
        "jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("school_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Enum("assessment_pdf", "assessment_docx", "report_card_pdf", "sba_report_card_pdf", "class_summary_csv", "term_exam_class_csv", name="job_type"), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "completed", "failed", "cancelled", name="job_status"), nullable=False, server_default="pending"),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("file_data", sa.LargeBinary(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_jobs_school_id", "jobs", ["school_id"])
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_unique_constraint("uq_jobs_idempotency_key", "jobs", ["idempotency_key"], postgresql_nulls_not_distinct=True)


def downgrade() -> None:
    op.drop_constraint("uq_jobs_idempotency_key", "jobs", type_="unique")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_index("ix_jobs_school_id", table_name="jobs")
    op.drop_table("jobs")
    op.execute("DROP TYPE job_status")
    op.execute("DROP TYPE job_type")
