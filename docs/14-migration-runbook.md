# 14 — Database Migration Runbook (Expand/Contract Pattern)

## Overview

This runbook governs **all** schema changes to the MwalimuKit production
database. It exists to prevent downtime and data loss when real users
depend on the system.

**Golden rule:** Never run a destructive migration directly on production.
Always run through staging first, with a documented rollback plan.

## Migration Framework

We use a custom expand/contract framework (`migrations/`) alongside
Alembic (`alembic/`).

| Layer               | Purpose                                      |
| ------------------- | -------------------------------------------- |
| `alembic/versions/` | Additive changes: new tables, indexes, enums |
| `migrations/versions/` | Destructive changes: renames, type changes, column drops |
| `alembic/`          | Auto-applied on deploy (via `alembic upgrade head`) |
| `migrations/`       | Manually triggered by operator with review    |

### When to use which

- **Use Alembic** for: new tables, new columns, indexes, constraints
- **Use migrations/** for: column renames, column type changes, column drops, table splits

The expand/contract pattern is mandatory for any change that touches
existing data.

## Expand/Contract Pattern

```
Phase 1: EXPAND   → Add new column/table alongside old one
Phase 2: MIGRATE  → Backfill data (batched, lock-free)
Phase 3: SWITCH   → Deploy code that reads/writes new shape
Phase 4: CONTRACT → Drop old column/table (after confirmation)
Phase 5: VERIFY   → Automated checks that migration succeeded
```

### Phase 1: EXPAND

**What happens:**
- New column/table is created
- Old column/table remains untouched
- Both shapes coexist; application continues using old shape

**Zero-downtime:** Yes. Old code still works.

**Example:**
```sql
ALTER TABLE users ADD COLUMN display_name TEXT;
CREATE INDEX CONCURRENTLY ix_users_display_name ON users(display_name);
```

**Rollback:**
```sql
DROP INDEX IF EXISTS ix_users_display_name;
ALTER TABLE users DROP COLUMN IF EXISTS display_name;
```
Risk: **SAFE** — old data untouched.

### Phase 2: MIGRATE

**What happens:**
- Data is copied from old column → new column
- Done in batches to avoid long locks
- Can run while application is live

**Zero-downtime:** Yes. Old code still writes to old column.

**Example:**
```sql
UPDATE users SET display_name = full_name WHERE display_name IS NULL;
```

**Batch pattern for large tables:**
```python
from migrations.utils import batch_update

await batch_update(
    conn,
    "UPDATE users SET display_name = full_name WHERE display_name IS NULL AND id IN (SELECT id FROM users WHERE display_name IS NULL LIMIT :limit)",
    batch_size=10_000
)
```

**Rollback:**
```sql
UPDATE users SET display_name = NULL WHERE display_name IS NOT NULL;
```
Risk: **REVERSIBLE** — old column still has original data.

### Phase 3: SWITCH

**What happens:**
- **Operator deploys new application code** that reads/writes the new column
- Application now uses `display_name`, ignores `full_name`
- Both columns still exist in database

**Zero-downtime:** Yes, **if**:
1. Application code reads from BOTH columns during transition
2. Application code writes to NEW column only
3. Old column is no longer modified by the app

**Critical:** Do NOT drop old column yet. Keep it as a fallback.

**Rollback:**
- Redeploy previous application version
- No SQL changes needed
Risk: **REVERSIBLE** (requires code revert)

### Phase 4: CONTRACT

**What happens:**
- Old column/table is dropped
- Only done after explicit human confirmation
- Requires verification that all traffic uses new shape

**Zero-downtime:** Yes, but **irreversible without backup**.

**Example:**
```sql
ALTER TABLE users DROP COLUMN full_name;
```

**Rollback:**
```sql
ALTER TABLE users ADD COLUMN full_name TEXT;
UPDATE users SET full_name = display_name WHERE full_name IS NULL;
```
Risk: **DESTRUCTIVE** — requires restore from backup if data was written to new column after switch.

### Phase 5: VERIFY

**What happens:**
- Automated checks confirm migration completeness
- Row counts, null checks, constraint checks

**Example:**
```python
def verify(conn):
    result = conn.execute("SELECT COUNT(*) FROM users WHERE display_name IS NULL")
    if result.scalar_one() > 0:
        raise RuntimeError("Users without display_name")
```

## Pre-Migration Checklist

Before ANY migration:

- [ ] **Backup taken** — `./scripts/backup.sh` or production snapshot
- [ ] **Staging tested** — migration runs clean on staging with real data
- [ ] **Rollback plan written** — every phase has a rollback function
- [ ] **Rollback tested** — rollback was tested on staging
- [ ] **Monitoring ready** — error rates, latency, DB connection counts
- [ ] **Team notified** — everyone knows migration is happening
- [ ] **Maintenance window** (if needed) — scheduled for high-risk phases
- [ ] **Feature flags ready** — ability to disable new code instantly

## Staging Environment

### Setup

```bash
# Start staging
docker compose -f infra/docker-compose.staging.yml up -d

# Verify staging is running
curl -f http://localhost:8001/health
```

### Refreshing staging from production

```bash
# 1. Take a fresh production backup
./scripts/backup.sh

# 2. Restore to staging
./scripts/refresh-staging.sh backups/mwalimukit-20260823T000000Z.dump.gz

# 3. Verify staging health
curl -f http://localhost:8001/ready
```

**Important:** Staging must be a **real mirror** of production, not a copy
of a development database. Real data patterns (volume, distribution,
null ratios) surface issues that synthetic data hides.

### Testing migrations on staging

```bash
# 1. Check current status
./scripts/migrate.sh status

# 2. Apply migration (pauses after switch)
./scripts/migrate.sh apply 0012_example_rename

# 3. Verify data integrity
./scripts/migrate.sh verify 0012_example_rename

# 4. Test application against migrated DB
# (hit staging endpoints, check for errors)

# 5. If all good, complete migration
./scripts/migrate.sh apply 0012_example_rename --no-confirm

# 6. Rollback test
./scripts/migrate.sh rollback 0012_example_rename
```

## Production Migration Steps

### Day -1: Preparation

1. Refresh staging from latest production backup
2. Run migration on staging
3. Verify data integrity on staging
4. Test rollback on staging
5. Review migration code with team
6. Schedule migration window

### Day 0: Migration

1. **Pre-migration backup** (mandatory)
   ```bash
   ./scripts/backup.sh
   ```

2. **Verify backup integrity**
   ```bash
   ls -lh backups/*.dump.gz
   gunzip -t backups/latest.dump.gz
   ```

3. **Start migration on staging** (already done in prep)
   ```bash
   ./scripts/migrate.sh apply 0012_example_rename
   # PAUSES after switch phase
   ```

4. **Deploy code to production** that reads/writes new columns
   ```bash
   ./scripts/deploy.sh production apply
   ```

5. **Verify production health**
   ```bash
   curl -f https://mwalimukit.co.ke/health
   curl -f https://mwalimukit.co.ke/ready
   docker compose logs -f api --tail=100
   ```

6. **Monitor for 30 minutes minimum**
   - Error rate (`/metrics` → `mwalimukit_http_requests_total`)
   - DB connection count
   - Query latency

7. **Complete migration** (only after confirmation)
   ```bash
   ./scripts/migrate.sh apply 0012_example_rename --no-confirm
   ```

8. **Verify completion**
   ```bash
   ./scripts/migrate.sh verify 0012_example_rename
   ./scripts/migrate.sh status
   ```

9. **Post-migration backup**
   ```bash
   ./scripts/backup.sh
   ```

## Rollback Procedure

### Immediate Rollback (< 5 minutes)

If something breaks **during any phase**:

```bash
# 1. Stop the migration
# (Ctrl+C or kill the process)

# 2. Rollback immediately
./scripts/migrate-rollback.sh 0012_example_rename

# 3. If rollback fails, restore from backup
./scripts/restore.sh backups/mwalimukit-20260823T000000Z.dump.gz

# 4. Verify health
curl -f https://mwalimukit.co.ke/health
```

### Rollback by Phase

| Phase | Rollback Action | Time | Risk |
| ----- | --------------- | ---- | ---- |
| EXPAND | Drop new columns | < 1 min | Safe |
| MIGRATE | Clear backfilled data | < 1 min | Reversible |
| SWITCH | Redeploy old code | 2-5 min | Reversible |
| CONTRACT | Restore from backup | 15-60 min | Destructive |
| VERIFY | Restore from backup | 15-60 min | Destructive |

## Rollback Decision Tree

```
Migration broken?
        │
        ▼
  During EXPAND/MIGRATE?
        │
   YES ─┴─── NO
    │          │
    ▼          ▼
 Drop new    During SWITCH?
 columns      │
 (safe)    YES ─┴─── NO
    │        │          │
    ▼        ▼          ▼
 Continue   Redeploy   Restore from
 monitoring  old code   backup
```

## Rollback Plan Template

Every migration **must** include this in its file:

```python
# migrations/versions/XXXX_migration_name.py

# ── ROLLBACK PLAN ──────────────────────────────────────────────
# Phase          | Risk Level   | Rollback Action                     | Time
# EXPAND         | SAFE         | Drop new columns                    | < 1 min
# MIGRATE        | REVERSIBLE   | Clear new column data               | < 1 min
# SWITCH         | REVERSIBLE   | Redeploy old application code       | 2-5 min
# CONTRACT       | DESTRUCTIVE  | Restore from pre-migration backup   | 15-60 min
# VERIFY         | DESTRUCTIVE  | Restore from pre-migration backup   | 15-60 min
#
# Pre-migration backup location: backups/mwalimukit-<timestamp>.dump.gz
# ──────────────────────────────────────────────────────────────
```

**If you cannot describe how to reverse any phase, the migration is NOT ready.**

## Monitoring During Migration

### Key metrics to watch

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| HTTP 5xx rate | `/metrics` → `mwalimukit_http_requests_total` | > 5% over 2 min |
| API latency p95 | `/metrics` → `mwalimukit_http_request_duration_seconds` | > 2s over 3 min |
| DB connections | `pg_stat_activity` | > 80% of max |
| DB lock waits | `pg_locks` | Any blocking > 5s |
| Replication lag | `pg_stat_replication` | > 30s (if applicable) |

### Quick health checks

```bash
# API health
curl -f https://mwalimukit.co.ke/health
curl -f https://mwalimukit.co.ke/ready

# DB connections
docker compose exec db psql -U mwalimu -d mwalimukit -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='mwalimukit';"

# Active locks
docker compose exec db psql -U mwalimu -d mwalimukit -c \
  "SELECT * FROM pg_locks WHERE granted = false;"

# Recent errors from logs
docker compose logs api --tail=200 | grep -i error | tail -20
```

## Common Patterns

### Renaming a column

```python
# migrations/versions/0012_rename_example.py

MIGRATION_ID = "0012_rename_example"

def expand(conn):
    conn.execute("ALTER TABLE users ADD COLUMN new_name TEXT")

def migrate(conn):
    conn.execute("UPDATE users SET new_name = old_name WHERE new_name IS NULL")

def switch(conn):
    conn.execute("COMMENT ON COLUMN users.old_name IS 'DEPRECATED'")

def contract(conn):
    conn.execute("ALTER TABLE users DROP COLUMN old_name")

def verify(conn):
    result = conn.execute("SELECT COUNT(*) FROM users WHERE new_name IS NULL")
    assert result.scalar_one() == 0
```

### Changing a column type

```python
def expand(conn):
    conn.execute("ALTER TABLE users ADD COLUMN age_new INTEGER")

def migrate(conn):
    conn.execute("UPDATE users SET age_new = CAST(age_text AS INTEGER) WHERE age_new IS NULL")

def switch(conn):
    # Deploy code that writes to age_new
    pass

def contract(conn):
    conn.execute("ALTER TABLE users DROP COLUMN age_text")
    conn.execute("ALTER TABLE users RENAME COLUMN age_new TO age")
```

### Adding a NOT NULL column

```python
def expand(conn):
    conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")

def migrate(conn):
    conn.execute("UPDATE users SET phone = '' WHERE phone IS NULL")

def contract(conn):
    conn.execute("ALTER TABLE users ALTER COLUMN phone SET NOT NULL")
```

## Emergency Contacts

| Role | Contact |
|------|---------|
| On-call engineer | [Slack #engineering-oncall] |
| Database admin | [Slack #database-admins] |
| Product owner | [Slack #mwalimukit-product] |

## Appendix: File Reference

| File | Purpose |
|------|---------|
| `migrations/runner.py` | Core expand/contract runner |
| `migrations/rollback.py` | Rollback plan definitions |
| `migrations/utils.py` | Batch update helpers |
| `migrations/versions/*.py` | Individual migration files |
| `migrations/cli.py` | CLI entry point |
| `scripts/migrate.sh` | Shell wrapper for migrations |
| `scripts/migrate-rollback.sh` | Rollback script |
| `scripts/migrate-status.sh` | Status checker |
| `scripts/refresh-staging.sh` | Refresh staging from production |
| `infra/docker-compose.staging.yml` | Staging environment |
| `docs/14-migration-runbook.md` | This document |
