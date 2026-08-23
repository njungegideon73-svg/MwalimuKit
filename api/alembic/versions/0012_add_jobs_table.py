"""Add jobs table for background export processing."""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotent: skip if jobs table already exists
    result = conn.execute(sa.text("SELECT to_regclass('public.jobs')"))
    if result.scalar() is not None:
        return

    # Clean up orphaned enums from a previous failed migration run
    conn.execute(sa.text("DROP TYPE IF EXISTS job_status"))
    conn.execute(sa.text("DROP TYPE IF EXISTS job_type"))

    conn.execute(sa.text("""
        CREATE TYPE job_type AS ENUM (
            'assessment_pdf',
            'assessment_docx',
            'report_card_pdf',
            'sba_report_card_pdf',
            'class_summary_csv',
            'term_exam_class_csv'
        )
    """))
    conn.execute(sa.text("""
        CREATE TYPE job_status AS ENUM (
            'pending',
            'processing',
            'completed',
            'failed',
            'cancelled'
        )
    """))

    conn.execute(sa.text("""
        CREATE TABLE jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
            type job_type NOT NULL,
            status job_status NOT NULL DEFAULT 'pending',
            payload JSONB NOT NULL DEFAULT '{}',
            result JSONB,
            file_data BYTEA,
            error TEXT,
            idempotency_key TEXT,
            expires_at TIMESTAMPTZ
        )
    """))

    conn.execute(sa.text("CREATE INDEX ix_jobs_school_id ON jobs (school_id)"))
    conn.execute(sa.text("CREATE INDEX ix_jobs_user_id ON jobs (user_id)"))
    conn.execute(sa.text("CREATE INDEX ix_jobs_status ON jobs (status)"))
    conn.execute(sa.text("""
        CREATE UNIQUE INDEX uq_jobs_idempotency_key ON jobs (idempotency_key)
    """))


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT to_regclass('public.jobs')"))
    if result.scalar() is None:
        return

    conn.execute(sa.text("DROP INDEX IF EXISTS uq_jobs_idempotency_key"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_jobs_status"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_jobs_user_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_jobs_school_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS jobs"))
    conn.execute(sa.text("DROP TYPE IF EXISTS job_status"))
    conn.execute(sa.text("DROP TYPE IF EXISTS job_type"))
