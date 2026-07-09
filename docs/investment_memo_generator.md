# P0.11 Investment Memo Generator Foundation

This sprint adds a deterministic investment research audit memo generator. It is an auxiliary reporting layer over existing artifacts and does not modify `schemas/output_schema.json`, `src/sws_engine/checks/`, `src/sws_engine/valuation/`, `src/sws_engine/growth/`, `src/sws_engine/portfolio/` or `config/assumptions.yaml`.

## Purpose

The memo answers: “Can I trust this analysis, and if not, why?” It does not answer which security to transact. The output is a research-process artifact, not investment advice.

## Inputs

Required:

- `audit_summary.json`

Optional:

- `explanation_package.json`
- `sensitivity_summary.json`
- `business_risk_package.json`
- `thesis_status.json`
- `decision_record.json`
- `portfolio_audit.json`

Missing optional artifacts remain visible as `MEMO_COMPONENT_UNKNOWN` and are added to `manual_review_items`.

## CLI

```bash
PYTHONPATH=src python -m sws_engine.cli generate-memo \
  --audit-summary tests/fixtures/investment_memo/AAPL_audit_summary.json \
  --business-risk tests/fixtures/investment_memo/AAPL_business_risk_package.json \
  --sensitivity tests/fixtures/investment_memo/AAPL_sensitivity_summary.json \
  --thesis-status tests/fixtures/investment_memo/AAPL_thesis_status.json \
  --portfolio-audit tests/fixtures/investment_memo/core_portfolio_audit.json \
  --output out/p11_ci
```

Artifacts:

- `<TICKER>_investment_audit_memo.json`
- `<TICKER>_investment_audit_memo.md`

## API

```text
POST /research/memo
```

Payload contains `audit_summary` and optional artifact objects. The endpoint returns `investment_memo`.

## Guardrails

The memo generator enforces:

- no recommendation-language;
- `UNKNOWN` preservation;
- source lineage visibility;
- not-investment-advice footer;
- false-precision guardrail for valuation display;
- deterministic template-based sections only.

## Out of scope

P0.11 does not implement dashboard pages, run comparison, transaction-based attribution, portfolio optimization, broker integration, live data fetching, sector-specific workflows or production-readiness PASS.
