#!/usr/bin/env bash
# Database backup script for UCT Benchmark
# Usage: ./scripts/backup_db.sh
# Requires: DATABASE_URL environment variable

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

BACKUP_FILE="$BACKUP_DIR/uct_benchmark_${TIMESTAMP}.sql.gz"
echo "Backing up to $BACKUP_FILE..."
pg_dump "$DATABASE_URL" --no-owner --no-acl | gzip > "$BACKUP_FILE"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/uct_benchmark_*.sql.gz | tail -n +8 | xargs -r rm --

echo "Backup complete: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
