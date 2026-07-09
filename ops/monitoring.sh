#!/usr/bin/env bash
set -euo pipefail
API_URL=${API_URL:-http://127.0.0.1:8000}
LOG_DIR=${LOG_DIR:-logs}
mkdir -p "$LOG_DIR"
python ops/monitoring.py --api-url "$API_URL" --logs-dir "$LOG_DIR"
