#!/usr/bin/env bash
# Full company research flow — real offline chain (P1.0).
# Mirrors README.md; exercised automatically by
# tests/e2e/test_full_research_flow_cli.py.
set -euo pipefail

FLOW_OUT=out/full_flow_example
mkdir -p "$FLOW_OUT"

PYTHONPATH=src python -m sws_engine.cli company \
  -i tests/fixtures/demo_complete_non_financial.json \
  --db "$FLOW_OUT/research.db" \
  -o "$FLOW_OUT/DEMO_engine_output.json"

PYTHONPATH=src python -m sws_engine.cli audit-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" --output "$FLOW_OUT/audit"

# Exit code 2 = honest UNKNOWN (manual fair value); not a failure.
PYTHONPATH=src python -m sws_engine.cli sensitivity-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" --output "$FLOW_OUT/sensitivity" || true

PYTHONPATH=src python -m sws_engine.cli explain-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" --output "$FLOW_OUT/explain"

PYTHONPATH=src python -m sws_engine.cli business-risk-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" --output "$FLOW_OUT/business_risk"

# P1.8: --auto resolves the latest artifacts from the SQLite index.
PYTHONPATH=src python -m sws_engine.cli generate-memo \
  --auto --ticker DEMO --db "$FLOW_OUT/research.db" \
  --output "$FLOW_OUT/memo"

# Optional release closure
PYTHONPATH=src python scripts/release/run_local_mvp_smoke.py --repo-root . --output out/p14_ci --release-id v4.0-mvp-p0.14
PYTHONPATH=src python scripts/ci/check_release_manifest.py out/p14_ci
