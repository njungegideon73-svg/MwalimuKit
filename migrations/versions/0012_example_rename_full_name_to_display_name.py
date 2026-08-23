"""Example zero-downtime migration: rename users.full_name → users.display_name.

This demonstrates the expand/contract pattern:
  EXPAND   — add display_name column, keep full_name
  MIGRATE  — backfill display_name from full_name
  SWITCH   — app starts writing to display_name, reading from both
  CONTRACT — drop full_name after confirmation

REQUIRED: every phase has a matching rollback_<phase>() function.
If you cannot describe how to reverse a phase, the migration is NOT ready.
"""
from __future__ import annotations

MIGRATION_ID = "0012_example_rename_full_name_to_display_name"
MIGRATION_NAME = "Rename users.full_name to users.display_name"


# ── EXPAND ─────────────────────────────────────────────────────────────
def expand(conn) -> None:
    """Add the new column alongside the old one. Both columns now exist."""
    conn.execute(
        """
        ALTER TABLE users
        ADD COLUMN display_name TEXT
        """
    )
    conn.execute(
        """
        CREATE INDEX CONCURRENTLY ix_users_display_name
        ON users(display_name)
        """
    )


def rollback_expand(conn) -> None:
    """Drop the new column. Old column remains intact."""
    conn.execute("DROP INDEX IF EXISTS ix_users_display_name")
    conn.execute("ALTER TABLE users DROP COLUMN IF EXISTS display_name")


# ── MIGRATE ─────────────────────────────────────────────────────────────
def migrate(conn) -> None:
    """Copy data from old column to new column in batches."""
    conn.execute(
        """
        UPDATE users
        SET display_name = full_name
        WHERE display_name IS NULL
        """
    )


def rollback_migrate(conn) -> None:
    """Clear the backfilled data from the new column."""
    conn.execute("UPDATE users SET display_name = NULL WHERE display_name IS NOT NULL")


# ── SWITCH ──────────────────────────────────────────────────────────────
def switch(conn) -> None:
    """Mark the old column as deprecated in metadata.
    The application code must be deployed BEFORE this runs so it
    reads/writes display_name and ignores full_name.
    """
    conn.execute(
        """
        COMMENT ON COLUMN users.full_name IS 'DEPRECATED: use display_name'
        """
    )
    conn.execute(
        """
        COMMENT ON COLUMN users.display_name IS 'Primary display name (replaces full_name)'
        """
    )


def rollback_switch(conn) -> None:
    """Remove deprecation comments. Application should be reverted first."""
    conn.execute("COMMENT ON COLUMN users.full_name IS NULL")
    conn.execute("COMMENT ON COLUMN users.display_name IS NULL")


# ── CONTRACT ────────────────────────────────────────────────────────────
def contract(conn) -> None:
    """Drop the old column after explicit human confirmation."""
    conn.execute("ALTER TABLE users DROP COLUMN full_name")


def rollback_contract(conn) -> None:
    """Re-add the old column. Data must be restored from backup."""
    conn.execute(
        """
        ALTER TABLE users
        ADD COLUMN full_name TEXT
        """
    )
    conn.execute(
        """
        UPDATE users
        SET full_name = display_name
        WHERE full_name IS NULL
        """
    )


# ── VERIFY ──────────────────────────────────────────────────────────────
def verify(conn) -> None:
    """Confirm the migration is complete."""
    result = conn.execute(
        """
        SELECT COUNT(*) FROM users
        WHERE display_name IS NULL
        """
    )
    null_count = result.scalar_one()
    if null_count > 0:
        raise RuntimeError(f"{null_count} users still have NULL display_name")

    result = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'full_name'
        """
    )
    if result.scalar_one_or_none() is not None:
        raise RuntimeError("old column 'full_name' still exists — contract phase incomplete")

    print("[verify] migration 0012 verified successfully")


ROLLBACK_SQL = """
-- Full rollback for migration 0012
-- Execute in reverse order:
-- 1. contract rollback: re-add full_name
ALTER TABLE users ADD COLUMN full_name TEXT;
UPDATE users SET full_name = display_name WHERE full_name IS NULL;

-- 2. switch rollback: clear comments
COMMENT ON COLUMN users.full_name IS NULL;
COMMENT ON COLUMN users.display_name IS NULL;

-- 3. migrate rollback: clear new column
UPDATE users SET display_name = NULL;

-- 4. expand rollback: drop new column/index
DROP INDEX IF EXISTS ix_users_display_name;
ALTER TABLE users DROP COLUMN IF EXISTS display_name;
"""
