"""Add feature_requests, feature_votes, prompt_history, subscriptions tables.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("vote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "feature_votes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("feature_id", UUID(as_uuid=True), sa.ForeignKey("feature_requests.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("feature_id", "user_id", name="uq_feature_vote"),
    )

    op.create_table(
        "prompt_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("assessment_id", UUID(as_uuid=True), sa.ForeignKey("assessments.id"), nullable=True),
        sa.Column("learning_area_code", sa.Text(), nullable=False),
        sa.Column("strand_code", sa.Text(), nullable=False),
        sa.Column("sub_strand_codes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("grade_level", sa.Text(), nullable=False),
        sa.Column("teacher_prompt", sa.Text(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("response_rubric", JSONB(), nullable=True),
        sa.Column("response_items", JSONB(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("school_id", UUID(as_uuid=True), sa.ForeignKey("schools.id"), nullable=False, unique=True),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("stripe_price_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="trialing"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("prompt_history")
    op.drop_table("feature_votes")
    op.drop_table("feature_requests")
