#!/usr/bin/env bash
# Daily refresh (Phase 4.3). No-network mode: steps 1 is a no-op until the
# live fetcher exists; the sequence and reporting are final.
set -uo pipefail
DATE="${1:-$(date +%F)}"
DB="data/sws.db"
python -m sws_engine.cli batch \
  --watchlist data/watchlists/watchlist_synthetic.csv \
  --date "$DATE" --db "$DB" \
  --universe data/universe/universe_US-SYN.csv --market US-SYN \
  --savings-rate 0.02 --cpi 0.028
