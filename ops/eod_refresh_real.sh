#!/usr/bin/env bash
set -euo pipefail

DATE="${1:-$(date +%F)}"
DB="${SWS_DB_PATH:-data/sws.db}"
WATCHLIST="${SWS_WATCHLIST:-data/watchlists/watchlist_synthetic.csv}"
UNIVERSE="${SWS_UNIVERSE:-data/universe/universe_US-SYN.csv}"
MARKET="${SWS_MARKET:-US-SYN}"
LOGS="${SWS_LOGS_DIR:-logs}"

python -m sws_engine.cli eod-refresh \
  --watchlist "$WATCHLIST" \
  --date "$DATE" \
  --db "$DB" \
  --universe "$UNIVERSE" \
  --market "$MARKET" \
  --logs-dir "$LOGS" \
  --provider-mode "${SWS_PROVIDER_MODE:-recorded}"
