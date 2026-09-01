"""Add schemes-of-work tables: lesson_content, schemes_of_work, scheme_lessons."""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(sa.text("SELECT to_regclass('public.lesson_content')"))
    if result.scalar() is not None:
        return

    conn.execute(sa.text("""
        CREATE TABLE lesson_content (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            sub_strand_code TEXT NOT NULL,
            term_number INTEGER NOT NULL,
            sequence_order INTEGER NOT NULL DEFAULT 0,
            topic TEXT NOT NULL,
            learning_outcomes JSONB NOT NULL DEFAULT '[]',
            learning_experiences JSONB NOT NULL DEFAULT '[]',
            key_inquiry_questions JSONB NOT NULL DEFAULT '[]',
            resources JSONB NOT NULL DEFAULT '[]',
            assessment_methods JSONB NOT NULL DEFAULT '[]',
            value_signs JSONB,
            core_competences JSONB
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX ix_lesson_content_sub_strand_code ON lesson_content (sub_strand_code)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX ix_lesson_content_term_number ON lesson_content (term_number)"
    ))

    conn.execute(sa.text("""
        CREATE TABLE schemes_of_work (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            sub_strand_code TEXT NOT NULL,
            grade TEXT NOT NULL,
            learning_area_code TEXT NOT NULL,
            term_number INTEGER NOT NULL,
            academic_year TEXT NOT NULL,
            lessons_per_week INTEGER NOT NULL DEFAULT 3,
            calendar_interruptions JSONB NOT NULL DEFAULT '[]',
            total_weeks INTEGER NOT NULL DEFAULT 0
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX ix_schemes_of_work_user_id ON schemes_of_work (user_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX ix_schemes_of_work_school_id ON schemes_of_work (school_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX ix_schemes_of_work_sub_strand_code ON schemes_of_work (sub_strand_code)"
    ))

    conn.execute(sa.text("""
        CREATE TABLE scheme_lessons (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            scheme_id UUID NOT NULL REFERENCES schemes_of_work(id) ON DELETE CASCADE,
            week_number INTEGER NOT NULL,
            lesson_number INTEGER NOT NULL,
            content_id UUID REFERENCES lesson_content(id),
            is_break BOOLEAN NOT NULL DEFAULT FALSE,
            break_label TEXT,
            strand_code TEXT,
            sub_strand_code TEXT,
            topic TEXT,
            learning_outcomes JSONB,
            learning_experiences JSONB,
            key_inquiry_questions JSONB,
            resources JSONB,
            assessment_methods JSONB,
            notes TEXT
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX ix_scheme_lessons_scheme_id ON scheme_lessons (scheme_id)"
    ))

    # Widen the job_type enum for the new scheme-of-work PDF export job.
    is_first_value_done = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'scheme_of_work_pdf')")
    ).scalar()
    if not is_first_value_done:
        conn.execute(sa.text(
            "ALTER TYPE job_type ADD VALUE IF NOT EXISTS 'scheme_of_work_pdf'"
        ))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_scheme_lessons_scheme_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS scheme_lessons"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_schemes_of_work_sub_strand_code"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_schemes_of_work_school_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_schemes_of_work_user_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS schemes_of_work"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_lesson_content_term_number"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_lesson_content_sub_strand_code"))
    conn.execute(sa.text("DROP TABLE IF EXISTS lesson_content"))