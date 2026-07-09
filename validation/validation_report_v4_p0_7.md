# Validation Report — v4.0 P0.7 Red Flags, Accounting Quality and Capital Allocation Foundation

## Scope implemented

Implemented the next controlled sprint after P0.6: **Red Flags, Accounting Quality and Capital Allocation Foundation**.

Implemented:

- `schemas/aux/business_risk_package.schema.json` for additive business-risk artifacts.
- `src/sws_engine/audit/risk_signals.py` package-level foundation for:
  - deterministic red-flag checks,
  - accounting quality metrics,
  - capital allocation metrics,
  - manual review item generation,
  - Markdown and JSON artifact generation.
- CLI `business-risk-company` for input-payload and persisted-run business-risk analysis.
- API endpoint `GET /companies/{ticker}/business-risks`.
- `docs/business_risk_signals.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.2` with P0.7 business-risk reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.7 reason codes.
- Offline fixtures under `tests/fixtures/business_risk/`.
- Tests under `tests/audit/` and `tests/api/` for:
  - business-risk package schema validation,
  - red flag detection,
  - accounting quality grading,
  - capital allocation assessment,
  - UNKNOWN preservation for missing business-risk inputs,
  - CLI smoke execution,
  - API endpoint smoke execution.

## P0.7 red flags implemented

P0.7 implements the first deterministic red-flag set:

- `NEGATIVE_OPERATING_CASH_FLOW`
- `NEGATIVE_FREE_CASH_FLOW`
- `EARNINGS_CASH_FLOW_DIVERGENCE`
- `DIVIDEND_NOT_COVERED_BY_FCF`
- `HIGH_INTANGIBLES_TO_ASSETS`
- `ELEVATED_NET_DEBT_TO_EQUITY`
- `SHARE_DILUTION_ABOVE_10PCT`
- `ENGINE_UNKNOWN_CHECKS_PRESENT`

Triggered flags are emitted in `red_flags`; all evaluated PASS/FAIL/UNKNOWN signals are preserved in `red_flag_checks`.

## P0.7 accounting quality metrics implemented

- `ACCRUALS_RATIO`
- `FCF_CONVERSION`
- `GROSS_MARGIN_VARIABILITY`

Output grade:

```text
STRONG / NORMAL / WATCH / WEAK / UNKNOWN
```

## P0.7 capital allocation metrics implemented

- `DIVIDENDS_TO_FCF`
- `BUYBACKS_TO_FCF`
- `CAPEX_INTENSITY`
- `SHARE_COUNT_GROWTH`

Output assessment:

```text
BALANCED / WATCH / UNKNOWN
```

## Explicitly not implemented

This sprint does **not** implement:

- Full forensic accounting.
- Sector-specific red flags.
- Bank-specific NPL / charge-off risk model.
- REIT AFFO / FFO / NAV risk model.
- Full source conflict detector runtime.
- Watchlist audit.
- Thesis tracker.
- Decision journal.
- Portfolio audit.
- Investment memo generator.
- Complex dashboard pages.
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
- UNKNOWN policy preserved: missing business-risk inputs return `UNKNOWN` with `BUSINESS_RISK_INPUTS_MISSING` and manual review items.
- Business-risk outputs are auxiliary audit artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli business-risk-company \
  --input tests/fixtures/business_risk/risk_payload.json \
  --output out/p07_ci
```

Result:

```text
PASS_WITH_LIMITATIONS; ticker=RISK; reason_code=BUSINESS_RISK_SIGNALS_COMPUTED; red_flags_count=4; accounting_quality_grade=WATCH; capital_allocation_assessment=WATCH
```

Artifacts:

```text
out/p07_ci/RISK_business_risk_package.json
out/p07_ci/RISK_business_risk_report.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources -q
```

Result:

```text
85 passed
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
191 passed, 2 skipped
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
PYTHONPATH=src python scripts/ci/check_audit_unknown_preserved.py out/audit_ci
PYTHONPATH=src python scripts/ci/check_source_registry_field_rules.py
PYTHONPATH=src python scripts/ci/check_reason_code_dictionary_complete.py
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
and reason-code dictionary completeness.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.7 implements a first deterministic business-risk foundation, not a full forensic accounting module.
2. Red flags depend only on supplied fields; missing values remain `UNKNOWN`.
3. Accounting quality and capital allocation outputs are auxiliary audit artifacts, not Snowflake scores.
4. Sector-specific models for banks, REITs, insurers, commodity cyclicals and pharma remain future work.
5. Production readiness remains blocked by curated source population and review, by design.
