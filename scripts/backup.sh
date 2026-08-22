#!/usr/bin/env bash
# MwalimuKit database backup.
#
# Dumps the Postgres database (custom format, gzip) into BACKUP_DIR and
# prunes backups older than RETENTION_DAYS.
#
# Usage:
#   ./scripts/backup.sh                       # uses docker compose service "db"
#   BACKUP_DIR=/var/backups ./scripts/backup.sh
#
# Environment:
#   COMPOSE_FILE   docker-compose file to use (default: ./docker-compose.yml)
#   BACKUP_DIR     output directory          (default: ./backups)
#   RETENTION_DAYS prune dumps older than N  (default: 14)
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/mwalimukit-$STAMP.dump.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] dumping database to $OUT"
$COMPOSE exec -T db pg_dump -U mwalimu -d mwalimukit -Fc \
  | gzip > "$OUT"

# ── Verify ───────────────────────────────────────────────────────────────────
SIZE=$(wc -c < "$OUT")
if [ "$SIZE" -lt 1024 ]; then
  echo "[backup] ERROR: dump suspiciously small ($SIZE bytes)" >&2
  rm -f "$OUT"
  exit 1
fi
if ! gunzip -t "$OUT"; then
  echo "[backup] ERROR: dump is not valid gzip" >&2
  exit 1
fi
if ! gunzip -c "$OUT" | head -c 5 | grep -q "PGDMP"; then
  echo "[backup] ERROR: dump is not a Postgres custom-format archive" >&2
  exit 1
fi

echo "[backup] OK ($SIZE bytes)"

# ── Prune old backups ────────────────────────────────────────────────────────
find "$BACKUP_DIR" -name 'mwalimukit-*.dump.gz' -type f -mtime +"$RETENTION_DAYS" -print -delete \
  | sed 's/^/[backup] pruned: /'

echo "[backup] done"
