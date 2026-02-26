#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/srv/stacks/hq"
LOCK_DIR="/tmp/hq-deploy.lock"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Deploy already running. Exiting."
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

cd "$REPO_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting HQ deploy..."
/usr/bin/git pull --ff-only
/usr/bin/docker compose up -d --build
echo "[$(date '+%Y-%m-%d %H:%M:%S')] HQ deploy complete."
