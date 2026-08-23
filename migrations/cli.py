"""CLI for MwalimuKit expand/contract migrations."""
from __future__ import annotations

import asyncio
import sys

from migrations.rollback import Phase, print_rollback_plan
from migrations.runner import MigrationRunner


def print_usage() -> None:
    print("Usage: python -m migrations.cli <command> [args]")
    print()
    print("Commands:")
    print("  status                              List all tracked migrations")
    print("  apply <migration_id> [--no-confirm]  Run migration phases")
    print("  rollback <migration_id>              Rollback a migration")
    print("  verify <migration_id>                Run verify() for a migration")
    print("  plan <migration_id>                  Print rollback plan")
    print()
    print("Examples:")
    print("  python -m migrations.cli status")
    print("  python -m migrations.cli apply 0012_example_rename")
    print("  python -m migrations.cli apply 0012_example_rename --no-confirm")
    print("  python -m migrations.cli rollback 0012_example_rename")


async def async_main() -> None:
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]
    migration_id = sys.argv[2] if len(sys.argv) > 2 else ""
    no_confirm = "--no-confirm" in sys.argv

    from app.core.db import engine

    async with engine.begin() as conn:
        runner = MigrationRunner(conn)
        await runner.ensure_migrations_table()

        if command == "status":
            records = await runner.list_records()
            if not records:
                print("No migrations tracked yet.")
            else:
                print(f"{'ID':<40} {'Phase':<12} {'Status':<12} {'Started':<20}")
                print("-" * 90)
                for r in records:
                    started = r.started_at.strftime("%Y-%m-%d %H:%M") if r.started_at else "-"
                    print(f"{r.id:<40} {r.phase:<12} {r.status:<12} {started:<20}")

        elif command == "apply":
            if not migration_id:
                print("Error: migration_id required for apply")
                sys.exit(1)
            await runner.apply(migration_id, confirm_after_switch=not no_confirm)

        elif command == "rollback":
            if not migration_id:
                print("Error: migration_id required for rollback")
                sys.exit(1)
            await runner.rollback(migration_id)

        elif command == "verify":
            if not migration_id:
                print("Error: migration_id required for verify")
                sys.exit(1)
            record = await runner.get_record(migration_id)
            if record is None:
                print("Migration not found.")
                sys.exit(1)
            module = runner._load_module(migration_id)
            verify_func = getattr(module, "verify", None)
            if verify_func is None:
                print("No verify() function defined for this migration.")
                sys.exit(1)
            import inspect
            sig = inspect.signature(verify_func)
            if len(sig.parameters) == 1:
                await verify_func(conn)
            else:
                await verify_func()
            print("Verify passed.")

        elif command == "plan":
            if not migration_id:
                print("Error: migration_id required for plan")
                sys.exit(1)
            record = await runner.get_record(migration_id)
            if record is None:
                print("Migration not found.")
                sys.exit(1)
            module = runner._load_module(migration_id)
            rollback_sql = getattr(module, "ROLLBACK_SQL", "")
            for phase in Phase:
                if phase.value in ["expand", "migrate", "switch", "contract", "verify"]:
                    from migrations.rollback import get_rollback_plan

                    p = get_rollback_plan(phase, rollback_sql)
                    print_rollback_plan(migration_id, p)

        else:
            print(f"Unknown command: {command}")
            print_usage()
            sys.exit(1)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
