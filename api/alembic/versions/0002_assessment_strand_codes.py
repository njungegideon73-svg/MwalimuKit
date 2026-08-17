"""Add strand_code and sub_strand_codes to assessments.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("strand_code", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("sub_strand_codes", ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "sub_strand_codes")
    op.drop_column("assessments", "strand_code")
