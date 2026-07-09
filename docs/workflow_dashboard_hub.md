# P0.13 — Research Workflow Package and Dashboard Hub

P0.13 adds a thin API/dashboard orchestration layer over artifacts already produced by the audit engine.
It is intentionally additive and does not change `schemas/output_schema.json`, Snowflake checks, valuation, growth, portfolio formulas or `config/assumptions.yaml`.

## Purpose

The workflow package answers one operational question:

> Which research-audit components are available for this ticker, which are missing, and where do UNKNOWN/manual-review items remain?

It does not answer whether an instrument is attractive. It emits no investment recommendation and no allocation guidance.

## Components tracked

The package tracks these workflow components:

- company audit summary;
- reason-code explanations;
- sensitivity and valuation range;
- business risk signals;
- thesis status;
- decision journal context;
- portfolio audit context;
- investment audit memo;
- run comparison.

Missing optional artifacts remain visible as `MISSING_OPTIONAL`. Missing required audit summary returns `UNKNOWN` with `WORKFLOW_PACKAGE_INPUTS_MISSING`.

## CLI

```bash
PYTHONPATH=src python -m sws_engine.cli workflow-package \
  --audit-summary tests/fixtures/investment_memo/AAPL_audit_summary.json \
  --explanations tests/fixtures/investment_memo/AAPL_explanations.json \
  --sensitivity tests/fixtures/investment_memo/AAPL_sensitivity_summary.json \
  --business-risk tests/fixtures/investment_memo/AAPL_business_risk_package.json \
  --thesis-status tests/fixtures/investment_memo/AAPL_thesis_status.json \
  --decision-record tests/fixtures/investment_memo/AAPL_decision_record.json \
  --portfolio-audit tests/fixtures/investment_memo/core_portfolio_audit.json \
  --run-comparison tests/fixtures/run_comparison/AAPL_current_audit_summary.json \
  --workflow-id p13-aapl \
  --output out/p13_ci
```

Outputs:

- `AAPL_workflow_package.json`
- `AAPL_workflow_package_report.md`

## API

New endpoints:

- `POST /research/workflow-package`
- `GET /companies/{ticker}/workflow`

The dashboard uses `dashboard.api_client.ApiClient` only. Streamlit pages must not import backend engine, database or orchestration internals.

## Dashboard

P0.13 adds:

- `dashboard/components/audit_workflow.py`
- `dashboard/pages/6_Audit_Workflow_Hub.py`

The page summarizes readiness, component status, UNKNOWN indicators, manual-review items and API wiring.

## Guardrails

- UNKNOWN indicators are counted and surfaced.
- Provider degradation remains visible through the audit artifact/manual-review items.
- Reports include the `Not investment advice` footer.
- Recommendation-language guardrail is enforced by `scripts/ci/check_workflow_package_guardrails.py`.
- Dashboard access remains API-only.
