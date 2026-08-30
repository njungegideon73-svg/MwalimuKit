"""Add created_by and school_id to feature_requests.

Revision ID: 0015
Revises: 0014_add_missing_indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0015"
down_revision = "0014_add_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("feature_requests", sa.Column("created_by", UUID(as_uuid=True), nullable=True))
    op.add_column("feature_requests", sa.Column("school_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_feature_requests_created_by", "feature_requests", "users", ["created_by"], ["id"])
    op.create_foreign_key("fk_feature_requests_school_id", "feature_requests", "schools", ["school_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_feature_requests_school_id", "feature_requests", type_="foreignkey")
    op.drop_constraint("fk_feature_requests_created_by", "feature_requests", type_="foreignkey")
    op.drop_column("feature_requests", "school_id")
    op.drop_column("feature_requests", "created_by")
