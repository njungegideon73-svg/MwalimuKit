"""Zero-downtime expand/contract migration runner for MwalimuKit.

Each migration is a Python module with four ordered phases:
  EXPAND   — add new columns / tables alongside existing ones (both live)
  MIGRATE  — backfill data from old → new in safe batches
  SWITCH   — deploy code that writes/reads the new shape
  CONTRACT — drop the old columns/tables AFTER explicit confirmation

The runner records progress in ``schema_migrations`` so it can be
paused, resumed, or rolled back at any phase.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

MIGRATIONS_DIR = Path(__file__).parent / "versions"
MIGRATIONS_TABLE = "schema_migrations"


@dataclass
class MigrationRecord:
    id: str
    name: str
    phase: str = "pending"
    status: str = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rolled_back_at: datetime | None = None
    rollback_sql: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class MigrationRunner:
    """Executes expand/contract migrations safely."""

    def __init__(self, connection: AsyncConnection) -> None:
        self._conn = connection
        self._dry_run = False

    def set_dry_run(self, dry: bool) -> None:
        self._dry_run = dry

    async def ensure_migrations_table(self) -> None:
        await self._conn.execute(
            text(f"""
                CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phase TEXT NOT NULL DEFAULT 'pending',
                    status TEXT NOT NULL DEFAULT 'pending',
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    rolled_back_at TIMESTAMPTZ,
                    rollback_sql TEXT DEFAULT '',
                    metadata JSONB DEFAULT '{{}}'
                )
            """)
        )

    async def get_record(self, migration_id: str) -> MigrationRecord | None:
        result = await self._conn.execute(
            text(f"SELECT * FROM {MIGRATIONS_TABLE} WHERE id = :id"),
            {"id": migration_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return MigrationRecord(
            id=row["id"],
            name=row["name"],
            phase=row["phase"],
            status=row["status"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            rolled_back_at=row["rolled_back_at"],
            rollback_sql=row["rollback_sql"],
            metadata=row["metadata"],
        )

    async def list_records(self) -> list[MigrationRecord]:
        result = await self._conn.execute(
            text(f"SELECT * FROM {MIGRATIONS_TABLE} ORDER BY id")
        )
        return [
            MigrationRecord(
                id=row["id"],
                name=row["name"],
                phase=row["phase"],
                status=row["status"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                rolled_back_at=row["rolled_back_at"],
                rollback_sql=row["rollback_sql"],
                metadata=row["metadata"],
            )
            for row in result.mappings().all()
        ]

    async def _update_record(self, record: MigrationRecord) -> None:
        await self._conn.execute(
            text(f"""
                INSERT INTO {MIGRATIONS_TABLE}
                    (id, name, phase, status, started_at, completed_at, rolled_back_at, rollback_sql, metadata)
                VALUES
                    (:id, :name, :phase, :status, :started_at, :completed_at, :rolled_back_at, :rollback_sql, :metadata)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    phase = EXCLUDED.phase,
                    status = EXCLUDED.status,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at,
                    rolled_back_at = EXCLUDED.rolled_back_at,
                    rollback_sql = EXCLUDED.rollback_sql,
                    metadata = EXCLUDED.metadata
            """),
            {
                "id": record.id,
                "name": record.name,
                "phase": record.phase,
                "status": record.status,
                "started_at": record.started_at,
                "completed_at": record.completed_at,
                "rolled_back_at": record.rolled_back_at,
                "rollback_sql": record.rollback_sql,
                "metadata": record.metadata,
            },
        )

    async def apply(self, migration_id: str, *, confirm_after_switch: bool = True) -> None:
        """Run a migration through all phases up to the current stop point."""
        record = await self.get_record(migration_id)
        if record is None:
            raise ValueError(f"Migration {migration_id} not found")

        if record.status == "completed":
            print(f"[migrate] {migration_id} already completed — skipping")
            return

        if record.status == "failed":
            print(f"[migrate] {migration_id} previously failed — rollback first")
            return

        now = datetime.now(timezone.utc)
        record.started_at = now
        record.status = "running"
        await self._update_record(record)

        module = self._load_module(migration_id)

        phases = ["expand", "migrate", "switch", "contract", "verify"]
        phase_idx = phases.index(record.phase) if record.phase in phases else -1

        try:
            for i, phase in enumerate(phases):
                if i <= phase_idx:
                    print(f"[migrate] {migration_id}: phase '{phase}' already done, skipping")
                    continue

                print(f"[migrate] {migration_id}: running phase '{phase}'")
                record.phase = phase
                await self._update_record(record)

                await self._run_phase(module, phase)

                record.phase = phase
                record.completed_at = datetime.now(timezone.utc)
                await self._update_record(record)

                if phase == "switch" and confirm_after_switch:
                    print("[migrate] PAUSED after 'switch'. Deploy code, verify, then re-run with --no-confirm.")
                    return

            record.status = "completed"
            record.phase = "completed"
            record.completed_at = datetime.now(timezone.utc)
            await self._update_record(record)
            print(f"[migrate] {migration_id} completed successfully")

        except Exception as exc:
            record.status = "failed"
            record.completed_at = datetime.now(timezone.utc)
            await self._update_record(record)
            print(f"[migrate] {migration_id} FAILED at phase '{record.phase}': {exc}")
            raise

    async def rollback(self, migration_id: str) -> None:
        """Rollback a migration to the 'pending' state."""
        record = await self.get_record(migration_id)
        if record is None:
            raise ValueError(f"Migration {migration_id} not found")

        if record.status == "pending":
            print(f"[rollback] {migration_id} is already pending — nothing to do")
            return

        print(f"[rollback] rolling back {migration_id} from phase '{record.phase}'...")

        module = self._load_module(migration_id)

        phases = ["expand", "migrate", "switch", "contract", "verify"]
        current_idx = phases.index(record.phase) if record.phase in phases else len(phases) - 1

        for i in range(current_idx, -1, -1):
            phase = phases[i]
            print(f"[rollback] undoing phase '{phase}'")
            await self._run_rollback_phase(module, phase)

        record.status = "rolled_back"
        record.phase = "pending"
        record.rolled_back_at = datetime.now(timezone.utc)
        await self._update_record(record)
        print(f"[rollback] {migration_id} rolled back successfully")

    async def _run_phase(self, module: Any, phase: str) -> None:
        func = getattr(module, phase, None)
        if func is None:
            print(f"[migrate] phase '{phase}' not defined in migration, skipping")
            return

        import inspect
        sig = inspect.signature(func)
        if len(sig.parameters) == 1:
            await func(self._conn)
        else:
            await func()

    async def _run_rollback_phase(self, module: Any, phase: str) -> None:
        rollback_func_name = f"rollback_{phase}"
        func = getattr(module, rollback_func_name, None)
        if func is None:
            print(f"[rollback] no rollback for phase '{phase}', skipping")
            return

        import inspect
        sig = inspect.signature(func)
        if len(sig.parameters) == 1:
            await func(self._conn)
        else:
            await func()

    def _load_module(self, migration_id: str) -> Any:
        path = MIGRATIONS_DIR / f"{migration_id}.py"
        if not path.exists():
            raise FileNotFoundError(f"Migration file not found: {path}")
        spec = importlib.util.spec_from_file_location(migration_id, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
