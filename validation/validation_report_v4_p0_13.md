# Validation Report — v4.0 P0.13 Research Workflow Package and Dashboard Hub Foundation

## Scope implemented

Implemented the next controlled sprint after P0.12: **Research Workflow Package and Dashboard Hub Foundation**.

Implemented:

- `schemas/aux/workflow_package.schema.json` for additive API/dashboard workflow artifacts.
- `src/sws_engine/research/workflow_package.py` for deterministic packaging of existing audit/research artifacts:
  - audit summary,
  - reason-code explanations,
  - sensitivity / valuation range,
  - business-risk package,
  - thesis status,
  - decision record,
  - portfolio audit context,
  - investment memo,
  - run comparison.
- CLI `workflow-package`.
- API endpoints:
  - `POST /research/workflow-package`,
  - `GET /companies/{ticker}/workflow`.
- Dashboard API client methods for P0.8–P0.13 workflow surfaces.
- Dashboard component `dashboard/components/audit_workflow.py`.
- Dashboard page `dashboard/pages/6_Audit_Workflow_Hub.py`.
- `docs/workflow_dashboard_hub.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.8` with P0.13 workflow reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.13 reason codes.
- Governance gate `scripts/ci/check_workflow_package_guardrails.py`.
- Offline fixtures under `tests/fixtures/workflow_package/`.
- Tests under `tests/research/`, `tests/api/`, and `tests/dashboard/` for:
  - workflow package schema validation,
  - UNKNOWN preservation,
  - missing optional component visibility,
  - missing required audit artifact handling,
  - CLI smoke execution,
  - API endpoint smoke execution,
  - dashboard API-client wiring,
  - dashboard component helpers,
  - API-only dashboard import guardrails,
  - report footer / recommendation-language guardrails.

## P0.13 workflow outputs implemented

P0.13 implements these auxiliary research-process outputs:

- `component_status`
- `workflow_steps`
- `readiness_summary`
- `unknown_summary`
- `manual_review_items`
- `api_wiring`
- `dashboard_surfaces`
- `input_lineage`
- `recommendation_guardrail`

These outputs are dashboard/API orchestration diagnostics, not v3.1 Snowflake checks and not investment recommendations.

## P0.13 reason codes added

- `WORKFLOW_PACKAGE_INPUTS_MISSING`
- `WORKFLOW_PACKAGE_READY`
- `WORKFLOW_COMPONENT_READY`
- `WORKFLOW_OPTIONAL_COMPONENT_MISSING`
- `WORKFLOW_PACKAGE_UNKNOWN_PRESERVED`
- `WORKFLOW_PACKAGE_MANUAL_REVIEW_REQUIRED`
- `WORKFLOW_DASHBOARD_API_ONLY`
- `WORKFLOW_NO_RECOMMENDATION_LANGUAGE`
- `WORKFLOW_RECOMMENDATION_LANGUAGE_REJECTED`

## Explicitly not implemented

This sprint does **not** implement:

- Complex multi-page dashboard redesign.
- Live data fetching.
- Transaction-based performance attribution.
- Portfolio optimization.
- Rebalancing recommendations.
- Broker integration.
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
- UNKNOWN policy preserved: components with UNKNOWN remain visible in `unknown_summary`, `component_status` and manual review items.
- Provider degradation remains visible through audit-summary derived manual review items.
- Workflow outputs are auxiliary dashboard/API artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Recommendation-language guardrail rejects forbidden wording.
- Dashboard remains API-only; Streamlit pages use `dashboard.api_client` and do not import engine/database internals.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli workflow-package \
  --audit-summary tests/fixtures/workflow_package/AAPL_audit_summary.json \
  --explanations tests/fixtures/workflow_package/AAPL_explanations.json \
  --sensitivity tests/fixtures/workflow_package/AAPL_sensitivity_summary.json \
  --business-risk tests/fixtures/workflow_package/AAPL_business_risk_package.json \
  --thesis-status tests/fixtures/workflow_package/AAPL_thesis_status.json \
  --decision-record tests/fixtures/workflow_package/AAPL_decision_record.json \
  --portfolio-audit tests/fixtures/workflow_package/core_portfolio_audit.json \
  --investment-memo out/p11_ci/AAPL_investment_audit_memo.json \
  --run-comparison out/p12_ci/AAPL_run_comparison.json \
  --workflow-id p13-aapl \
  --output out/p13_ci
```

Result:

```text
PASS_WITH_LIMITATIONS; reason_code=WORKFLOW_PACKAGE_UNKNOWN_PRESERVED; ticker=AAPL;
workflow_id=p13-aapl; ready_count=4; manual_review_count=5;
total_unknown_indicators=32; recommendation_language_absent=true
```

Artifacts:

```text
out/p13_ci/AAPL_workflow_package.json
out/p13_ci/AAPL_workflow_package_report.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/research tests/api -q
```

Result:

```text
61 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/dashboard tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources -q
```

Result:

```text
81 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/averages_real tests/ci tests/contract tests/data_layer tests/deploy tests/docs \
  tests/gold tests/governance tests/integration tests/manual tests/ops tests/persistence \
  tests/portfolio tests/providers tests/synthetic -q
```

Result:

```text
89 passed
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
231 passed, 2 skipped
```

A single all-in-one pytest run was attempted but timed out in the sandbox after partial progress, so the reliable result is the segmented coverage above.

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
PYTHONPATH=src python scripts/ci/check_workflow_package_guardrails.py out/p13_ci
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
reason-code dictionary completeness, watchlist report guardrails, thesis/decision guardrails,
portfolio audit guardrails, investment memo guardrails, run comparison guardrails and
workflow package guardrails.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.13 packages and displays supplied/existing artifacts only; it does not rerun the engine or fetch live data.
2. `GET /companies/{ticker}/workflow` builds from persisted company audit only; optional deep-dive artifacts are supplied through `POST /research/workflow-package`.
3. The new dashboard page is a foundation/hub, not a full dashboard redesign.
4. Workflow readiness is process readiness, not an economic conclusion.
5. Production readiness remains blocked by curated source population and review, by design.
