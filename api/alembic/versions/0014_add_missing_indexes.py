"""Add missing composite and single-column indexes for frequent query patterns.

Revision ID: 0014_add_missing_indexes
Revises: 0013
Create Date: 2026-08-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # term_exams: common filters by school + class + year, and school + class + created_at
    op.create_index(
        "ix_term_exams_school_class_year",
        "term_exams",
        ["school_id", "class_id", "academic_year"],
        unique=False,
    )
    op.create_index(
        "ix_term_exams_school_class_created",
        "term_exams",
        ["school_id", "class_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )

    # activity_logs: filter by school + date range
    op.create_index(
        "ix_activity_logs_school_created",
        "activity_logs",
        ["school_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )

    # jobs: filter by school + status, user + status, and expired cleanup
    op.create_index("ix_jobs_school_status", "jobs", ["school_id", "status"], unique=False)
    op.create_index("ix_jobs_user_status", "jobs", ["user_id", "status"], unique=False)
    op.create_index(
        "ix_jobs_expires_at",
        "jobs",
        ["expires_at"],
        unique=False,
        postgresql_where="expires_at IS NOT NULL",
    )

    # users: filter active users by school
    op.create_index("ix_users_school_active", "users", ["school_id", "is_active"], unique=False)

    # feature_votes: check if a user voted on any feature
    op.create_index("ix_feature_votes_user", "feature_votes", ["user_id"], unique=False)

    # prompt_history: filter by school
    op.create_index("ix_prompt_history_school", "prompt_history", ["school_id"], unique=False)

    # assessment_runs: find all runs for a given assessment
    op.create_index("ix_runs_school_assessment", "assessment_runs", ["school_id", "assessment_id"], unique=False)

    # subscriptions: filter by status (active, trialing, etc.)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_runs_school_assessment", table_name="assessment_runs")
    op.drop_index("ix_prompt_history_school", table_name="prompt_history")
    op.drop_index("ix_feature_votes_user", table_name="feature_votes")
    op.drop_index("ix_users_school_active", table_name="users")
    op.drop_index("ix_jobs_expires_at", table_name="jobs")
    op.drop_index("ix_jobs_user_status", table_name="jobs")
    op.drop_index("ix_jobs_school_status", table_name="jobs")
    op.drop_index("ix_activity_logs_school_created", table_name="activity_logs")
    op.drop_index("ix_term_exams_school_class_created", table_name="term_exams")
    op.drop_index("ix_term_exams_school_class_year", table_name="term_exams")
