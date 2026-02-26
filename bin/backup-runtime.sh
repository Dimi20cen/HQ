#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/srv/stacks/hq"
SOURCE_DIR="$REPO_DIR/runtime"
BACKUP_DIR="$REPO_DIR/backups/runtime"
LOCK_DIR="/tmp/hq-backup-runtime.lock"
RETENTION_DAYS=35

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Backup already running. Exiting."
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

mkdir -p "$BACKUP_DIR"

ts="$(date '+%Y%m%d-%H%M%S')"
archive="$BACKUP_DIR/runtime-$ts.tar.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Creating backup: $archive"
/usr/bin/tar -C "$REPO_DIR" -czf "$archive" runtime

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pruning backups older than $RETENTION_DAYS days"
/usr/bin/find "$BACKUP_DIR" -type f -name 'runtime-*.tar.gz' -mtime +"$RETENTION_DAYS" -delete

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete"
