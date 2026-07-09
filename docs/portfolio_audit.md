# Portfolio Audit Minimal — v4.0 P0.10

P0.10 adds a deterministic local portfolio audit layer. It is an auxiliary research artifact and does not change the v3.1 portfolio engine, checks, valuation, growth model or `schemas/output_schema.json`.

## Scope

The portfolio audit consumes a local holdings CSV and already-produced artifacts:

- audit summaries,
- business-risk packages,
- thesis-status packages,
- sensitivity summaries.

It emits:

- weighted data confidence,
- weighted conclusion risk,
- unknown exposure,
- provider-degradation exposure,
- sector concentration,
- factor concentration,
- macro sensitivity map,
- single-thesis concentration,
- attribution-lite by supplied current value,
- manual review items.

## Non-goals

P0.10 does not provide portfolio allocation advice, buy/sell/hold language, optimization, rebalancing, broker integration, live data fetching or a public/commercial workflow.

## CLI

```bash
PYTHONPATH=src python -m sws_engine.cli portfolio-audit \
  --holdings tests/fixtures/portfolio_audit/holdings.csv \
  --audit-dir tests/fixtures/portfolio_audit/audits \
  --business-risk-dir tests/fixtures/portfolio_audit/business_risks \
  --thesis-dir tests/fixtures/portfolio_audit/theses \
  --sensitivity-dir tests/fixtures/portfolio_audit/sensitivity \
  --portfolio-id core \
  --output out/p10_ci
```

## UNKNOWN policy

Missing artifacts are not inferred. A holding without an audit summary is kept in the portfolio and contributes to `unknown_exposure`. Missing macro/factor/thesis labels remain `UNKNOWN` and generate manual review items where material.

## Guardrails

- No canonical `output_schema.json` changes.
- No changes to `src/sws_engine/checks/`, `valuation/`, `growth/` or `portfolio/`.
- No `score_normalized` output.
- No investment recommendation language.
- Reports include the attribution and not-investment-advice footer.
