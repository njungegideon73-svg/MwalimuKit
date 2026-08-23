"""Enable PostgreSQL Row-Level Security on newly tenant-scoped tables.

Extends the RLS coverage from migration 0009 to tables that were
retrospectively fitted with a ``school_id`` column in 0010:
  - ``news_items``
  - ``scores``
  - ``learner_exam_scores``

Policies use the same GUCs (``app.current_school_id``, ``app.role``)
and super-admin bypass pattern as the existing RLS setup.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-22 13:00:00.000000
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "news_items",
    "scores",
    "learner_exam_scores",
]


def _enable_rls(table: str) -> None:
    for p in ["select", "insert", "update", "delete"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{p}_{table} ON {table}")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY rls_select_{table} ON {table}
        FOR SELECT
        USING (
            school_id = current_setting('app.current_school_id', true)::uuid
            OR current_setting('app.role', true) = 'super_admin'
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY rls_insert_{table} ON {table}
        FOR INSERT
        WITH CHECK (
            school_id = current_setting('app.current_school_id', true)::uuid
            OR current_setting('app.role', true) = 'super_admin'
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY rls_update_{table} ON {table}
        FOR UPDATE
        USING (
            school_id = current_setting('app.current_school_id', true)::uuid
            OR current_setting('app.role', true) = 'super_admin'
        )
        WITH CHECK (
            school_id = current_setting('app.current_school_id', true)::uuid
            OR current_setting('app.role', true) = 'super_admin'
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY rls_delete_{table} ON {table}
        FOR DELETE
        USING (
            school_id = current_setting('app.current_school_id', true)::uuid
            OR current_setting('app.role', true) = 'super_admin'
        )
        """
    )


def _disable_rls(table: str) -> None:
    for p in ["select", "insert", "update", "delete"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{p}_{table} ON {table}")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    for table in TENANT_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in TENANT_TABLES:
        _disable_rls(table)
