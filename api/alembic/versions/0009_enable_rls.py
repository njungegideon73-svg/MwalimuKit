"""Enable PostgreSQL Row-Level Security on tenant-scoped tables.

Implements defense-in-depth: the application already scopes queries by
``school_id`` in SQLAlchemy, but RLS guarantees that even a bug in
application code cannot leak one school's rows to another.

Strategy:
- Only tables with a direct ``school_id`` column get tenant policies.
- A GUC (Grand Unified Configuration) ``app.current_school_id`` is set
  per-connection from the authenticated user's ``school_id`` (see
  ``api/app/core/tenant.py`` middleware).
- The ``users`` table additionally allows email-based SELECT so the
  login/signup endpoints can look up users before a full tenant context
  is established (the middleware sets ``app.current_email`` for auth
  routes).
- Super-admins bypass tenant scope via ``app.role = 'super_admin'``.

Revision ID: 0009_rls
Revises: 0008
Create Date: 2026-08-22 00:00:00.000000
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# Only tables with a direct school_id column.  Reference data (learning_areas,
# strands, sub_strands) and root entities (schools) are intentionally excluded.
# Tables scoped indirectly (scores, learner_exam_scores, news_items, ...) keep
# their existing application-level filtering; adding subquery-based RLS there
# would complicate migrations without meaningful gain.
TENANT_TABLES = [
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

# users needs an extra email-based policy for authentication.
_EXTRA_POLICIES = {
    "users": """
        CREATE POLICY rls_auth_user_by_email ON users
        FOR SELECT
        USING (
            email = current_setting('app.current_email', true)
            OR current_setting('app.role', true) = 'super_admin'
        )
        """,
}


def _drop_policies(table: str) -> None:
    policy_names = ["select", "insert", "update", "delete"]
    if table == "users":
        policy_names.append("auth_user_by_email")
    for p in policy_names:
        # The auth policy does not carry the table suffix.
        name = "rls_auth_user_by_email" if p == "auth_user_by_email" else f"rls_{p}_{table}"
        op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")


def _enable_rls(table: str) -> None:
    _drop_policies(table)
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
    extra = _EXTRA_POLICIES.get(table)
    if extra:
        op.execute(extra)


def _disable_rls(table: str) -> None:
    policy_names = ["select", "insert", "update", "delete"]
    if table == "users":
        policy_names.append("auth_user_by_email")
    for p in policy_names:
        name = "rls_auth_user_by_email" if p == "auth_user_by_email" else f"rls_{p}_{table}"
        op.execute(f"DROP POLICY IF EXISTS {name} ON {table}")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # Initialise GUCs with defaults so policies never error on NULL casts.
    op.execute("SELECT set_config('app.current_school_id', '', false)")
    op.execute("SELECT set_config('app.role', 'app', false)")
    op.execute("SELECT set_config('app.current_email', '', false)")
    for table in TENANT_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in TENANT_TABLES:
        _disable_rls(table)
