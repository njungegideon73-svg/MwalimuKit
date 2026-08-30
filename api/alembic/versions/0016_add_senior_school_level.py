"""Add senior_school to curriculum_level enum.

Adds the Senior School (Grades 10-12) level to support Kenya's full
2-6-3-3-3 CBC structure:
  - Early Years: PP1, PP2, Grades 1-3 (lower_primary)
  - Middle School: Grades 4-6 (upper_primary), Grades 7-9 (jss)
  - Senior School: Grades 10-12 (senior_school)

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add senior_school to the curriculum_level enum type
    op.execute("ALTER TYPE curriculum_level ADD VALUE IF NOT EXISTS 'senior_school'")

    # Update the CHECK constraint on learning_areas to include the new value
    op.execute("ALTER TABLE learning_areas DROP CONSTRAINT IF EXISTS ck_learning_area_level")
    op.execute(
        "ALTER TABLE learning_areas ADD CONSTRAINT ck_learning_area_level "
        "CHECK (level IN ('lower_primary', 'upper_primary', 'jss', 'senior_school'))"
    )


def downgrade() -> None:
    # Revert the CHECK constraint
    op.execute("ALTER TABLE learning_areas DROP CONSTRAINT IF EXISTS ck_learning_area_level")
    op.execute(
        "ALTER TABLE learning_areas ADD CONSTRAINT ck_learning_area_level "
        "CHECK (level IN ('lower_primary', 'upper_primary', 'jss'))"
    )

    # Note: PostgreSQL does not support removing values from an ENUM type.
    # The 'senior_school' value will remain in the type but will no longer
    # be accepted by the CHECK constraint. Manual cleanup would be required
    # to fully remove it (altering the type to a new type).
