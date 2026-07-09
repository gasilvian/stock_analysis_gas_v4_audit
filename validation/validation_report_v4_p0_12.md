# Validation Report — v4.0 P0.12 Run Comparison / Change Detection Foundation

## Scope implemented

Implemented the next controlled sprint after P0.11: **Run Comparison / Change Detection Foundation**.

Implemented:

- `schemas/aux/run_comparison.schema.json` for additive run-comparison artifacts.
- `src/sws_engine/research/run_comparison.py` for deterministic local comparison of two run/audit artifacts:
  - run identity changes,
  - assumptions hash changes,
  - provider profile changes,
  - score and coverage deltas,
  - check result and reason-code changes when `checks[]` exists,
  - new/resolved UNKNOWN checks,
  - critical missing inputs added/resolved,
  - component changes for data confidence, model applicability and conclusion risk,
  - warning deltas,
  - best-effort field-lineage deltas,
  - manual review item generation.
- CLI `compare-runs`.
- API endpoint `POST /research/compare-runs`.
- `docs/run_comparison.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.7` with P0.12 run-comparison reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.12 reason codes.
- Governance gate `scripts/ci/check_run_comparison_guardrails.py`.
- Offline fixtures under `tests/fixtures/run_comparison/`.
- Tests under `tests/research/` and `tests/api/test_api_run_comparison.py` for:
  - run-comparison package schema validation,
  - UNKNOWN preservation,
  - assumptions hash/provider profile change detection,
  - score/coverage delta detection,
  - check-level new UNKNOWN detection,
  - lineage-change detection,
  - CLI smoke execution,
  - API endpoint smoke execution,
  - report footer / recommendation-language guardrails.

## P0.12 run comparison outputs implemented

P0.12 implements these auxiliary research-process outputs:

- `metadata_changes`
- `score_changes`
- `checks_changes`
- `component_changes`
- `unknown_changes`
- `lineage_changes`
- `warnings_changes`
- `material_change_count`
- `manual_review_items`
- `recommendation_guardrail`

These outputs are process diagnostics, not v3.1 Snowflake checks and not investment recommendations.

## P0.12 reason codes added

- `RUN_COMPARISON_INPUTS_MISSING`
- `RUN_COMPARISON_COMPUTED`
- `RUN_COMPARISON_CHANGES_DETECTED`
- `RUN_COMPARISON_NO_MATERIAL_CHANGE`
- `RUN_COMPARISON_UNKNOWN_PRESERVED`
- `RUN_COMPARISON_NO_UNKNOWN_DETECTED`
- `RUN_COMPARISON_CHECKS_CHANGED`
- `RUN_COMPARISON_CHECKS_UNCHANGED_OR_UNAVAILABLE`
- `RUN_COMPARISON_LINEAGE_CHANGED`
- `RUN_COMPARISON_LINEAGE_UNCHANGED_OR_UNAVAILABLE`
- `RUN_COMPARISON_NO_RECOMMENDATION_LANGUAGE`
- `RUN_COMPARISON_RECOMMENDATION_LANGUAGE_REJECTED`

## Explicitly not implemented

This sprint does **not** implement:

- Complex dashboard pages.
- Transaction-based performance attribution.
- Portfolio optimization.
- Rebalancing recommendations.
- Broker integration.
- Live data fetching.
- Full source conflict detector runtime.
- Sector-specific bank / REIT / insurer workflows.
- Automatic integration into canonical `output_schema.json`.
- Production-readiness PASS.
- Any investment recommendation text.
- BUY / SELL / HOLD language.

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved: current UNKNOWN checks and critical missing inputs remain visible in `unknown_changes` and manual review items.
- Provider degradation remains visible through `metadata_changes`, warnings deltas and manual review items.
- Run comparison outputs are auxiliary research-workflow artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Recommendation-language guardrail rejects forbidden wording.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli compare-runs \
  --previous tests/fixtures/run_comparison/AAPL_previous_audit_summary.json \
  --current tests/fixtures/run_comparison/AAPL_current_audit_summary.json \
  --comparison-id p12-aapl \
  --output out/p12_ci
```

Result:

```text
PASS_WITH_LIMITATIONS; reason_code=RUN_COMPARISON_UNKNOWN_PRESERVED; ticker=AAPL;
comparison_id=p12-aapl; material_change_count=18; new_unknown_count=2;
recommendation_language_absent=true
```

Artifacts:

```text
out/p12_ci/AAPL_run_comparison.json
out/p12_ci/AAPL_run_comparison_report.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/research tests/api -q
```

Result:

```text
55 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources -q
```

Result:

```text
61 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/averages_real tests/ci tests/contract tests/dashboard tests/data_layer tests/deploy \
  tests/docs tests/gold tests/governance tests/integration tests/manual tests/ops \
  tests/persistence tests/portfolio tests/providers tests/synthetic -q
```

Result:

```text
106 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/e2e tests/live -q
```

Result:

```text
2 skipped
```

Total segmented coverage:

```text
222 passed, 2 skipped
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
PYTHONPATH=src python scripts/ci/check_audit_unknown_preserved.py tests/fixtures/watchlist/audits
PYTHONPATH=src python scripts/ci/check_source_registry_field_rules.py
PYTHONPATH=src python scripts/ci/check_reason_code_dictionary_complete.py
PYTHONPATH=src python scripts/ci/check_watchlist_report_guardrails.py out/p08_ci
PYTHONPATH=src python scripts/ci/check_thesis_decision_guardrails.py out/p09_ci
PYTHONPATH=src python scripts/ci/check_portfolio_audit_guardrails.py out/p10_ci
PYTHONPATH=src python scripts/ci/check_investment_memo_guardrails.py out/p11_ci
PYTHONPATH=src python scripts/ci/check_run_comparison_guardrails.py out/p12_ci
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
reason-code dictionary completeness, watchlist report guardrails, thesis/decision guardrails,
portfolio audit guardrails, investment memo guardrails and run comparison guardrails.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.12 compares supplied local artifacts only; it does not rerun the engine or fetch live data.
2. Check-level comparison is only available when both artifacts contain `checks[]`.
3. Lineage comparison is best-effort and depends on lineage objects present in supplied artifacts.
4. The module detects changes; it does not decide whether changes are economically positive or negative.
5. No dashboard integration is included in this sprint.
6. Production readiness remains blocked by curated source population and review, by design.
