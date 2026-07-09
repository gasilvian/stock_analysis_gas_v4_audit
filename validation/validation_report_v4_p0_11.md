# Validation Report — v4.0 P0.11 Investment Memo Generator Foundation

## Scope implemented

Implemented the next controlled sprint after P0.10: **Investment Memo Generator Foundation**.

Implemented:

- `schemas/aux/investment_memo.schema.json` for additive investment-memo artifacts.
- `src/sws_engine/reporting/investment_memo.py` for deterministic company research audit memos from existing artifacts:
  - audit summary,
  - reason-code explanations,
  - sensitivity / valuation range,
  - business-risk package,
  - thesis status,
  - decision record,
  - portfolio audit context.
- CLI `generate-memo`.
- API endpoint `POST /research/memo`.
- `docs/investment_memo_generator.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.6` with P0.11 memo reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.11 reason codes.
- Governance gate `scripts/ci/check_investment_memo_guardrails.py`.
- Offline fixtures under `tests/fixtures/investment_memo/`.
- Tests under `tests/research/` and `tests/api/test_api_investment_memo.py` for:
  - investment-memo package schema validation,
  - UNKNOWN preservation,
  - missing optional component visibility,
  - false-precision valuation-range guardrail,
  - recommendation-language guardrail,
  - CLI smoke execution,
  - API endpoint smoke execution,
  - not-investment-advice footer/report guardrails.

## P0.11 memo outputs implemented

P0.11 implements these auxiliary research-process outputs:

- `component_status`
- `sections.executive_audit_view`
- `sections.score_and_coverage`
- `sections.data_confidence`
- `sections.model_applicability`
- `sections.conclusion_risk`
- `sections.sensitivity_and_valuation_range`
- `sections.business_risk`
- `sections.thesis_status`
- `sections.decision_context`
- `sections.portfolio_context`
- `sections.unknown_and_limitations`
- `unknown_summary`
- `manual_review_items`
- `recommendation_guardrail`
- `false_precision_guardrail`
- `input_lineage`

These outputs are deterministic memo/reporting artifacts, not v3.1 Snowflake checks and not investment recommendations.

## P0.11 reason codes added

- `MEMO_INPUTS_MISSING`
- `MEMO_GENERATED`
- `MEMO_COMPONENT_UNKNOWN`
- `MEMO_UNKNOWN_PRESERVED`
- `MEMO_FALSE_PRECISION_GUARDRAIL_APPLIED`
- `MEMO_RECOMMENDATION_LANGUAGE_REJECTED`
- `MEMO_NO_RECOMMENDATION_LANGUAGE`
- `MEMO_MANUAL_REVIEW_REQUIRED`

## Explicitly not implemented

This sprint does **not** implement:

- Run comparison.
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
- UNKNOWN policy preserved: missing optional memo inputs remain visible as `MEMO_COMPONENT_UNKNOWN` and manual review items.
- Provider degradation remains visible through audit summary / memo manual review items.
- Memo outputs are auxiliary research-workflow/reporting artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Recommendation-language guardrail rejects forbidden wording.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli generate-memo \
  --audit-summary tests/fixtures/investment_memo/AAPL_audit_summary.json \
  --explanations tests/fixtures/investment_memo/AAPL_explanations.json \
  --sensitivity tests/fixtures/investment_memo/AAPL_sensitivity_summary.json \
  --business-risk tests/fixtures/investment_memo/AAPL_business_risk_package.json \
  --thesis-status tests/fixtures/investment_memo/AAPL_thesis_status.json \
  --decision-record tests/fixtures/investment_memo/AAPL_decision_record.json \
  --portfolio-audit tests/fixtures/investment_memo/core_portfolio_audit.json \
  --output out/p11_ci
```

Result:

```text
PASS_WITH_LIMITATIONS; reason_code=MEMO_MANUAL_REVIEW_REQUIRED; ticker=AAPL; memo_type=investment_audit; recommendation_language_absent=true
```

Artifacts:

```text
out/p11_ci/AAPL_investment_audit_memo.json
out/p11_ci/AAPL_investment_audit_memo.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/research tests/api -q
```

Result:

```text
49 passed
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
216 passed, 2 skipped
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
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
reason-code dictionary completeness, watchlist report guardrails, thesis/decision guardrails,
portfolio audit guardrails and investment memo guardrails.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.11 generates deterministic Markdown/JSON memos only; it does not interpret free-form thesis text or create AI narratives.
2. Memo quality depends on supplied audit/business-risk/sensitivity/thesis/decision/portfolio artifacts.
3. Missing optional artifacts remain `UNKNOWN` and are explicitly listed.
4. Fair-value presentation depends on the sensitivity artifact; without it, the memo does not promote a point fair value.
5. No run comparison or dashboard integration is included in this sprint.
6. Production readiness remains blocked by curated source population and review, by design.
