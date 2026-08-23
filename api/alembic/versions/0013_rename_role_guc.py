"""Rename RLS GUC from app.current_role to app.role.

current_role is a PostgreSQL reserved keyword; using it as a custom GUC
name causes syntax errors with the RESET command and complicates policy
management.  Rename to app.role everywhere.

Revision ID: 0013_rename_role_guc
Revises: 0012
Create Date: 2026-08-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

# Tables from migration 0009
_TENANT_TABLES_0009 = [
    "users",
    "classes",
    "learners",
    "assessments",
    "assessment_runs",
    "term_exams",
    "subscriptions",
    "prompt_history",
    "activity_logs",
]

# Tables from migration 0011
_TENANT_TABLES_0011 = [
    "news_items",
    "scores",
    "learner_exam_scores",
]


def _drop_policies(table: str) -> None:
    policy_names = ["select", "insert", "update", "delete"]
    if table == "users":
        policy_names.append("auth_user_by_email")
    for p in policy_names:
        name = f"rls_{p}_{table}"
        op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")


def _create_policies(table: str) -> None:
    # SELECT policy
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
    # INSERT policy
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
    # UPDATE policy
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
    # DELETE policy
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
    # Extra auth policy for users table
    if table == "users":
        op.execute(
            """
            CREATE POLICY rls_auth_user_by_email ON users
            FOR SELECT
            USING (
                email = current_setting('app.current_email', true)
                OR current_setting('app.role', true) = 'super_admin'
            )
            """
        )


def upgrade() -> None:
    conn = op.get_bind()

    # Update GUC default value
    conn.execute(sa.text("SELECT set_config('app.role', 'app', false)"))

    # Recreate policies for 0009 tables
    for table in _TENANT_TABLES_0009:
        _drop_policies(table)
        _create_policies(table)

    # Recreate policies for 0011 tables
    for table in _TENANT_TABLES_0011:
        _drop_policies(table)
        _create_policies(table)


def downgrade() -> None:
    conn = op.get_bind()

    # Restore old GUC name
    conn.execute(sa.text("SELECT set_config('app.current_role', 'app', false)"))

    # Restore old policies for 0009 tables
    for table in _TENANT_TABLES_0009:
        _drop_policies(table)
        # Recreate with old name
        op.execute(
            f"""
            CREATE POLICY rls_select_{table} ON {table}
            FOR SELECT
            USING (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        op.execute(
            f"""
            CREATE POLICY rls_insert_{table} ON {table}
            FOR INSERT
            WITH CHECK (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        op.execute(
            f"""
            CREATE POLICY rls_update_{table} ON {table}
            FOR UPDATE
            USING (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            WITH CHECK (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        op.execute(
            f"""
            CREATE POLICY rls_delete_{table} ON {table}
            FOR DELETE
            USING (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        if table == "users":
            op.execute(
                """
                CREATE POLICY rls_auth_user_by_email ON users
                FOR SELECT
                USING (
                    email = current_setting('app.current_email', true)
                    OR current_setting('app.current_role', true) = 'super_admin'
                )
                """
            )

    # Restore old policies for 0011 tables
    for table in _TENANT_TABLES_0011:
        _drop_policies(table)
        op.execute(
            f"""
            CREATE POLICY rls_select_{table} ON {table}
            FOR SELECT
            USING (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        op.execute(
            f"""
            CREATE POLICY rls_insert_{table} ON {table}
            FOR INSERT
            WITH CHECK (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        op.execute(
            f"""
            CREATE POLICY rls_update_{table} ON {table}
            FOR UPDATE
            USING (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            WITH CHECK (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
        op.execute(
            f"""
            CREATE POLICY rls_delete_{table} ON {table}
            FOR DELETE
            USING (
                school_id = current_setting('app.current_school_id', true)::uuid
                OR current_setting('app.current_role', true) = 'super_admin'
            )
            """
        )
