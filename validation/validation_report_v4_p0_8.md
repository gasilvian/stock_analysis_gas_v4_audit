# Validation Report — v4.0 P0.8 Watchlist Audit Foundation

## Scope implemented

Implemented the next controlled sprint after P0.7: **Watchlist Audit Foundation**.

Implemented:

- `schemas/aux/watchlist_audit.schema.json` for additive watchlist-triage artifacts.
- `src/sws_engine/research/` package:
  - `__init__.py`
  - `watchlist.py`
- CLI `audit-watchlist` for local watchlist CSV triage from existing audit/business-risk artifacts.
- API endpoint `POST /audit/watchlist` for in-memory watchlist triage.
- `docs/watchlist_audit.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.3` with P0.8 watchlist reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.8 reason codes.
- Governance gate `scripts/ci/check_watchlist_report_guardrails.py`.
- Offline fixtures under `tests/fixtures/watchlist/`.
- Tests under `tests/research/` and `tests/api/test_api_watchlist_audit.py` for:
  - watchlist package schema validation,
  - deterministic bucket triage,
  - missing audit artifact UNKNOWN preservation,
  - provider degradation visibility,
  - CLI smoke execution,
  - API endpoint smoke execution,
  - report footer / no recommendation-language guardrails.

## P0.8 buckets implemented

P0.8 implements deterministic process buckets:

- `Researchable Now`
- `Data Limited`
- `Needs Different Model`
- `Ignore for Now`
- `Manual Review Required`

These buckets are process-triage outputs, not investment recommendations and not buy/sell/hold signals.

## P0.8 reason codes added

- `WATCHLIST_AUDIT_COMPUTED`
- `WATCHLIST_INPUTS_MISSING`
- `WATCHLIST_AUDIT_ARTIFACTS_MISSING`
- `WATCHLIST_AUDIT_ARTIFACT_MISSING`
- `WATCHLIST_TICKER_MISSING`
- `WATCHLIST_RESEARCHABLE_NOW`
- `WATCHLIST_DATA_LIMITED`
- `WATCHLIST_NEEDS_DIFFERENT_MODEL`
- `WATCHLIST_NOT_APPLICABLE_IGNORED`
- `WATCHLIST_MODEL_APPLICABILITY_UNKNOWN`
- `WATCHLIST_CONCLUSION_RISK_REVIEW_REQUIRED`
- `WATCHLIST_RED_FLAGS_REVIEW_REQUIRED`
- `WATCHLIST_PROVIDER_DEGRADED`

## Explicitly not implemented

This sprint does **not** implement:

- Thesis tracker.
- Decision journal.
- Portfolio audit.
- Investment memo generator.
- Complex dashboard pages.
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
- UNKNOWN policy preserved: tickers without audit artifacts remain `Data Limited` with `artifact_status=UNKNOWN` and `WATCHLIST_AUDIT_ARTIFACT_MISSING`.
- yfinance/provider degradation remains visible through `WATCHLIST_PROVIDER_DEGRADED`.
- Watchlist outputs are auxiliary research-workflow artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli audit-watchlist \
  --watchlist tests/fixtures/watchlist/watchlist.csv \
  --audit-dir tests/fixtures/watchlist/audits \
  --business-risk-dir tests/fixtures/watchlist/business_risks \
  --output out/p08_ci
```

Result:

```text
PASS_WITH_LIMITATIONS; reason_code=WATCHLIST_AUDIT_COMPUTED; watchlist_size=3;
bucket_counts={Researchable Now: 1, Data Limited: 1, Needs Different Model: 1,
Ignore for Now: 0, Manual Review Required: 0}; manual_review_count=2; unknown_artifact_count=1
```

Artifacts:

```text
out/p08_ci/watchlist_audit.json
out/p08_ci/watchlist_audit_report.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources tests/research -q
```

Result:

```text
90 passed
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
196 passed, 2 skipped
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
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
reason-code dictionary completeness and watchlist report guardrails.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.8 implements watchlist triage only; thesis tracker and decision journal remain future work.
2. Watchlist buckets depend on existing audit/business-risk artifacts; missing artifacts remain UNKNOWN.
3. Bucket assignment is workflow prioritization, not investment advice.
4. No dashboard re-scope was implemented in this sprint.
5. Production readiness remains blocked by curated source population and review, by design.
