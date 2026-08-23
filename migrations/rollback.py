"""Rollback plan definitions for each expand/contract migration phase.

Every migration **must** implement rollback for every phase it defines.
If a rollback path cannot be described, the migration is not ready to run.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Phase(str, Enum):
    EXPAND = "expand"
    MIGRATE = "migrate"
    SWITCH = "switch"
    CONTRACT = "contract"
    VERIFY = "verify"


class RollbackRisk(str, Enum):
    SAFE = "safe"
    REVERSIBLE = "reversible"
    DESTRUCTIVE = "destructive"
    REQUIRES_RESTORE = "requires_restore"


@dataclass
class RollbackPlan:
    phase: Phase
    risk: RollbackRisk
    description: str
    sql: str = ""
    requires_code_revert: bool = False
    requires_manual_action: str | None = None


STANDARD_ROLLBACK_PLANS = {
    Phase.EXPAND: RollbackPlan(
        phase=Phase.EXPAND,
        risk=RollbackRisk.SAFE,
        description="Drop any columns/tables added in the expand phase. Old schema is untouched.",
        sql="-- Drop new columns added in expand phase\n-- (old columns still exist and contain all data)",
    ),
    Phase.MIGRATE: RollbackPlan(
        phase=Phase.MIGRATE,
        risk=RollbackRisk.REVERSIBLE,
        description="Delete data copied into new columns. Old data remains intact in original columns.",
        sql="-- Delete backfilled rows from new columns\n-- Old columns retain original data",
        requires_manual_action="If data was modified in new columns during the switch phase, manual merge may be required.",
    ),
    Phase.SWITCH: RollbackPlan(
        phase=Phase.SWITCH,
        risk=RollbackRisk.REVERSIBLE,
        description="Redeploy previous application version that reads/writes old columns. Both columns exist during this phase.",
        sql="-- No SQL needed — redeploy old app version",
        requires_code_revert=True,
    ),
    Phase.CONTRACT: RollbackPlan(
        phase=Phase.CONTRACT,
        risk=RollbackRisk.DESTRUCTIVE,
        description="Old columns have been dropped. Must restore from pre-migration backup if data was lost.",
        sql="-- Re-add old columns from backup\n-- RESTORE FROM LATEST PRE-MIGRATION BACKUP",
        requires_manual_action="Restore from the pre-migration backup taken at the start of EXPAND phase. Data written to new columns during SWITCH may need manual re-entry.",
    ),
    Phase.VERIFY: RollbackPlan(
        phase=Phase.VERIFY,
        risk=RollbackRisk.DESTRUCTIVE,
        description="Migration is fully complete. Rollback requires restoring from backup.",
        sql="-- Full restore required\n-- RESTORE FROM LATEST PRE-MIGRATION BACKUP",
        requires_manual_action="Restore from the pre-migration backup taken at the start of EXPAND phase.",
    ),
}


def get_rollback_plan(phase: Phase, migration_specific_sql: str = "") -> RollbackPlan:
    """Return the rollback plan for a given phase, augmented with migration-specific SQL."""
    plan = STANDARD_ROLLBACK_PLANS[phase]
    if migration_specific_sql:
        plan = RollbackPlan(
            phase=plan.phase,
            risk=plan.risk,
            description=plan.description,
            sql=f"{plan.sql}\n\n{migration_specific_sql}",
            requires_code_revert=plan.requires_code_revert,
            requires_manual_action=plan.requires_manual_action,
        )
    return plan


def print_rollback_plan(migration_id: str, plan: RollbackPlan) -> None:
    print(f"\n{'='*60}")
    print(f"ROLLBACK PLAN: {migration_id} — phase '{plan.phase.value}'")
    print(f"{'='*60}")
    print(f"Risk:        {plan.risk.value.upper()}")
    print(f"Description: {plan.description}")
    if plan.sql:
        print(f"\nSQL:\n{plan.sql}")
    if plan.requires_code_revert:
        print("\nACTION REQUIRED: Redeploy previous application version.")
    if plan.requires_manual_action:
        print(f"\nMANUAL ACTION: {plan.requires_manual_action}")
    print(f"{'='*60}\n")
