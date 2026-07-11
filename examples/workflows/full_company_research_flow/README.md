# Full Company Research Flow — Real Offline Chain (P1.0)

This example runs the **actual research chain end to end** on the committed
demo payload — engine run, persistence, audit layer, sensitivity, deterministic
explanations, business-risk signals and the investment research audit memo.
It replaces the earlier fixture-only example: every artifact consumed below is
produced by the previous step, not read from `tests/fixtures/`.

Everything is offline. No network, no live data, no API keys.

```bash
# 0. Work area
export FLOW_OUT=out/full_flow_example
mkdir -p "$FLOW_OUT"

# 1. Run the v3.1 engine on the demo payload and persist the run
#    (--db is optional single-run persistence added in P1.0; the batch
#    command remains the multi-ticker path).
PYTHONPATH=src python -m sws_engine.cli company \
  -i tests/fixtures/demo_complete_non_financial.json \
  --db "$FLOW_OUT/research.db" \
  -o "$FLOW_OUT/DEMO_engine_output.json"

# 2. Audit layer on the persisted run (data confidence, model applicability,
#    conclusion risk, missing inputs, UNKNOWN preserved).
PYTHONPATH=src python -m sws_engine.cli audit-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" \
  --output "$FLOW_OUT/audit"

# 3. Sensitivity / valuation range. The demo payload uses a manual fair value,
#    so the honest result is UNKNOWN (exit code 2 by CLI convention) — the
#    engine never invents a base case.
PYTHONPATH=src python -m sws_engine.cli sensitivity-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" \
  --output "$FLOW_OUT/sensitivity" || true

# 4. Deterministic reason-code explanations.
PYTHONPATH=src python -m sws_engine.cli explain-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" \
  --output "$FLOW_OUT/explain"

# 5. Red flags / accounting quality / capital allocation signals.
PYTHONPATH=src python -m sws_engine.cli business-risk-company \
  --ticker DEMO --db "$FLOW_OUT/research.db" \
  --output "$FLOW_OUT/business_risk"

# 6. Investment research audit memo. With P1.8, steps 2-5 registered their
#    outputs in the SQLite artifact index, so --auto resolves the latest
#    artifacts per kind — no hand-wired paths. Unproduced kinds (thesis,
#    decision, portfolio) stay honestly UNKNOWN in the memo.
PYTHONPATH=src python -m sws_engine.cli generate-memo \
  --auto --ticker DEMO --db "$FLOW_OUT/research.db" \
  --output "$FLOW_OUT/memo"

# 7. (Optional) Release closure: local MVP smoke + manifest guardrail.
PYTHONPATH=src python scripts/release/run_local_mvp_smoke.py \
  --repo-root . --output out/p14_ci --release-id v4.0-mvp-p0.14
PYTHONPATH=src python scripts/ci/check_release_manifest.py out/p14_ci
```

The same chain is exercised automatically by
`tests/e2e/test_full_research_flow_cli.py`.

**P2.1:** the entire chain above (steps 1–6, plus the source-conflict report)
can now be run with a single command — see
`docs/research_company_orchestrator.md`:

```bash
PYTHONPATH=src python -m sws_engine.cli research-company \
  --input tests/fixtures/demo_complete_non_financial.json \
  --db "$FLOW_OUT/research.db" --output "$FLOW_OUT/chain"
```

Notes:
- Replace the demo payload with a real recorded snapshot / built payload to run
  the chain on a real company; every governance rule (UNKNOWN preserved,
  provider degradation visible, no recommendation language) applies unchanged.
- `thesis-status`, `record-decision`, `portfolio-audit`, `compare-runs` and
  `workflow-package` extend this chain with the research-discipline artifacts.

All outputs are research-audit artifacts. They do not provide investment
advice and contain no BUY/SELL/HOLD language.
