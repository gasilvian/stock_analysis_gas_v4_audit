#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=${BACKUP_DIR:-backups}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BACKUP_DIR"
ARCHIVE="$BACKUP_DIR/sws_backup_${STAMP}.tar.gz"
tar -czf "$ARCHIVE" \
  data/sws.db \
  validation/snapshots \
  config \
  schemas \
  2>/dev/null || true
printf '{"backup":"%s","created_at":"%s"}\n' "$ARCHIVE" "$STAMP"
