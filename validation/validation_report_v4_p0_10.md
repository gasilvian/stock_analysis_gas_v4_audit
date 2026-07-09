# Validation Report — v4.0 P0.10 Portfolio Audit Minimal Foundation

## Scope implemented

Implemented the next controlled sprint after P0.9: **Portfolio Audit Minimal Foundation**.

Implemented:

- `schemas/aux/portfolio_audit.schema.json` for additive portfolio-audit artifacts.
- `src/sws_engine/audit/portfolio_audit.py` for deterministic local portfolio audit:
  - weighted data confidence,
  - weighted conclusion risk,
  - unknown exposure,
  - provider-degradation exposure,
  - sector concentration,
  - factor concentration,
  - macro sensitivity map,
  - single-thesis concentration,
  - attribution-lite from supplied current values,
  - manual review item generation.
- CLI `portfolio-audit`.
- API endpoint `POST /audit/portfolio`.
- `docs/portfolio_audit.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.5` with P0.10 portfolio-audit reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.10 reason codes.
- Governance gate `scripts/ci/check_portfolio_audit_guardrails.py`.
- Offline fixtures under `tests/fixtures/portfolio_audit/`.
- Tests under `tests/audit/` and `tests/api/test_api_portfolio_audit.py` for:
  - portfolio package schema validation,
  - weighted data confidence and conclusion risk,
  - unknown exposure preservation,
  - provider degradation exposure visibility,
  - concentration summaries,
  - macro sensitivity map from operator labels,
  - CLI smoke execution,
  - API endpoint smoke execution,
  - report footer / no recommendation-language guardrails.

## P0.10 portfolio audit metrics implemented

P0.10 implements these auxiliary research-process outputs:

- `weighted_data_confidence`
- `weighted_conclusion_risk`
- `unknown_exposure`
- `provider_degradation_exposure`
- `sector_concentration`
- `factor_concentration`
- `macro_sensitivity_map`
- `single_thesis_concentration`
- `attribution_lite`
- per-holding `manual_review_items`

These outputs are process diagnostics, not investment recommendations and not buy/sell/hold signals.

## P0.10 reason codes added

- `PORTFOLIO_INPUTS_MISSING`
- `PORTFOLIO_AUDIT_ARTIFACTS_MISSING`
- `PORTFOLIO_AUDIT_COMPUTED`
- `PORTFOLIO_WEIGHTED_DATA_CONFIDENCE_COMPUTED`
- `PORTFOLIO_WEIGHTED_CONCLUSION_RISK_COMPUTED`
- `PORTFOLIO_UNKNOWN_EXPOSURE_PRESENT`
- `PORTFOLIO_NO_UNKNOWN_EXPOSURE`
- `PORTFOLIO_PROVIDER_DEGRADATION_EXPOSURE`
- `PORTFOLIO_NO_PROVIDER_DEGRADATION_EXPOSURE`
- `PORTFOLIO_CONCENTRATION_COMPUTED`
- `PORTFOLIO_CONCENTRATION_HIGH`
- `PORTFOLIO_MACRO_EXPOSURE_COMPUTED`
- `PORTFOLIO_MACRO_EXPOSURE_UNKNOWN`
- `PORTFOLIO_ATTRIBUTION_LITE_COMPUTED`
- `PORTFOLIO_ATTRIBUTION_INPUTS_MISSING`
- `PORTFOLIO_COMPONENT_UNKNOWN`

## Explicitly not implemented

This sprint does **not** implement:

- Investment memo generator.
- Run comparison.
- Complex dashboard pages.
- Portfolio optimization.
- Rebalancing recommendations.
- Broker integration.
- Live data fetching.
- Full performance attribution from transactions.
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
- UNKNOWN policy preserved: holdings without audit artifacts remain included and increase `unknown_exposure`.
- Provider degradation remains visible through `provider_degradation_exposure` and per-holding manual review items.
- Portfolio audit outputs are auxiliary research-workflow artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli portfolio-audit \
  --holdings tests/fixtures/portfolio_audit/holdings.csv \
  --audit-dir tests/fixtures/portfolio_audit/audits \
  --business-risk-dir tests/fixtures/portfolio_audit/business_risks \
  --thesis-dir tests/fixtures/portfolio_audit/theses \
  --sensitivity-dir tests/fixtures/portfolio_audit/sensitivity \
  --portfolio-id core \
  --valuation-date 2026-07-09 \
  --output out/p10_ci
```

Result:

```text
PASS_WITH_LIMITATIONS; reason_code=PORTFOLIO_AUDIT_COMPUTED; portfolio_id=core;
holdings_count=5; weighted_data_confidence=MEDIUM; weighted_conclusion_risk=MEDIUM;
unknown_exposure_pct=10.0
```

Artifacts:

```text
out/p10_ci/core_portfolio_audit.json
out/p10_ci/core_portfolio_audit_report.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources tests/research -q
```

Equivalent segmented result:

```text
105 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/averages_real tests/ci tests/contract tests/dashboard tests/data_layer tests/deploy \
  tests/docs tests/gold tests/governance tests/integration tests/manual tests/ops \
  tests/persistence tests/portfolio tests/providers tests/synthetic -q
```

Equivalent segmented result:

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
211 passed, 2 skipped
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
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
reason-code dictionary completeness, watchlist report guardrails, thesis/decision guardrails
and portfolio audit guardrails.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.10 implements minimal local portfolio audit only; it does not optimize or recommend allocation.
2. Portfolio audit depends on supplied holdings and existing audit/business-risk/thesis/sensitivity artifacts.
3. Missing artifacts remain `UNKNOWN` and contribute to unknown exposure.
4. Attribution-lite uses supplied `current_value`; it is not transaction-based performance attribution.
5. Production readiness remains blocked by curated source population and review, by design.
