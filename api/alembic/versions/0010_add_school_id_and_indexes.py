"""Add school_id to news_items, scores, learner_exam_scores and add performance indexes.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-22 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- news_items ---
    op.add_column("news_items", sa.Column("school_id", UUID(as_uuid=True), nullable=False, server_default="00000000-0000-0000-0000-000000000000"))
    conn.execute("""
        UPDATE news_items
        SET school_id = users.school_id
        FROM users
        WHERE news_items.created_by = users.id
    """)
    op.alter_column("news_items", "school_id", server_default=None)
    op.create_foreign_key("fk_news_items_school_id", "news_items", "schools", ["school_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_news_items_school_created", "news_items", ["school_id", "created_at"])
    op.create_index("ix_news_items_active_created", "news_items", ["is_active", "created_at"])

    # --- scores ---
    op.add_column("scores", sa.Column("school_id", UUID(as_uuid=True), nullable=False, server_default="00000000-0000-0000-0000-000000000000"))
    conn.execute("""
        UPDATE scores
        SET school_id = assessment_runs.school_id
        FROM assessment_runs
        WHERE scores.run_id = assessment_runs.id
    """)
    op.alter_column("scores", "school_id", server_default=None)
    op.create_foreign_key("fk_scores_school_id", "scores", "schools", ["school_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_scores_school_run_learner", "scores", ["school_id", "run_id", "learner_id"])
    op.create_index("ix_scores_run_id", "scores", ["run_id"])

    # --- learner_exam_scores ---
    op.add_column("learner_exam_scores", sa.Column("school_id", UUID(as_uuid=True), nullable=False, server_default="00000000-0000-0000-0000-000000000000"))
    conn.execute("""
        UPDATE learner_exam_scores
        SET school_id = term_exams.school_id
        FROM term_exams
        WHERE learner_exam_scores.term_exam_id = term_exams.id
    """)
    op.alter_column("learner_exam_scores", "school_id", server_default=None)
    op.create_foreign_key("fk_learner_exam_scores_school_id", "learner_exam_scores", "schools", ["school_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_learner_exam_scores_school_exam", "learner_exam_scores", ["school_id", "term_exam_id", "learner_id"])

    # --- learners indexes ---
    op.create_index("ix_learners_school_class_deleted", "learners", ["school_id", "class_id"], unique=False)
    op.create_index("ix_learners_school_id_deleted", "learners", ["school_id", "id"], unique=False, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_learners_class_id", "learners", ["class_id"], unique=False)

    # --- classes indexes ---
    op.create_index("ix_classes_school_teacher_deleted", "classes", ["school_id", "teacher_id"], unique=False, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_classes_school_id_deleted", "classes", ["school_id", "id"], unique=False, postgresql_where="deleted_at IS NULL")

    # --- assessments indexes ---
    op.create_index("ix_assessments_school_deleted_updated", "assessments", ["school_id", "deleted_at", "updated_at"], unique=False, postgresql_where="deleted_at IS NULL")
    op.create_index("ix_assessments_school_id_deleted", "assessments", ["school_id", "id"], unique=False, postgresql_where="deleted_at IS NULL")

    # --- assessment_runs indexes ---
    op.create_index("ix_runs_school_class_started", "assessment_runs", ["school_id", "class_id", "started_at"], unique=False)
    op.create_index("ix_runs_school_id", "assessment_runs", ["school_id", "id"], unique=False)

    # --- users index ---
    op.create_index("ix_users_school_role", "users", ["school_id", "role"], unique=False)

    # --- subscriptions index ---
    op.create_index("ix_subscriptions_stripe_sub_id", "subscriptions", ["stripe_subscription_id"], unique=False)

    # --- prompt_history index ---
    op.create_index("ix_prompt_history_user_created", "prompt_history", ["user_id", "created_at"], unique=False, postgresql_ops={"created_at": "DESC"})


def downgrade() -> None:
    op.drop_index("ix_prompt_history_user_created", table_name="prompt_history")
    op.drop_index("ix_subscriptions_stripe_sub_id", table_name="subscriptions")
    op.drop_index("ix_users_school_role", table_name="users")
    op.drop_index("ix_runs_school_id", table_name="assessment_runs")
    op.drop_index("ix_runs_school_class_started", table_name="assessment_runs")
    op.drop_index("ix_assessments_school_id_deleted", table_name="assessments")
    op.drop_index("ix_assessments_school_deleted_updated", table_name="assessments")
    op.drop_index("ix_classes_school_id_deleted", table_name="classes")
    op.drop_index("ix_classes_school_teacher_deleted", table_name="classes")
    op.drop_index("ix_learners_class_id", table_name="learners")
    op.drop_index("ix_learners_school_id_deleted", table_name="learners")
    op.drop_index("ix_learners_school_class_deleted", table_name="learners")

    op.drop_index("ix_learner_exam_scores_school_exam", table_name="learner_exam_scores")
    op.drop_constraint("fk_learner_exam_scores_school_id", "learner_exam_scores", type_="foreignkey")
    op.alter_column("learner_exam_scores", "school_id", server_default="00000000-0000-0000-0000-000000000000")
    op.drop_column("learner_exam_scores", "school_id")

    op.drop_index("ix_scores_run_id", table_name="scores")
    op.drop_index("ix_scores_school_run_learner", table_name="scores")
    op.drop_constraint("fk_scores_school_id", "scores", type_="foreignkey")
    op.alter_column("scores", "school_id", server_default="00000000-0000-0000-0000-000000000000")
    op.drop_column("scores", "school_id")

    op.drop_index("ix_news_items_active_created", table_name="news_items")
    op.drop_index("ix_news_items_school_created", table_name="news_items")
    op.drop_constraint("fk_news_items_school_id", "news_items", type_="foreignkey")
    op.alter_column("news_items", "school_id", server_default="00000000-0000-0000-0000-000000000000")
    op.drop_column("news_items", "school_id")
