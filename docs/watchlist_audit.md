# Watchlist Audit — v4.0 P0.8

P0.8 adds the first research-workflow layer: deterministic watchlist triage.
It consumes existing audit artifacts from previous sprints and places each ticker into one of five process buckets:

- `Researchable Now`
- `Data Limited`
- `Needs Different Model`
- `Ignore for Now`
- `Manual Review Required`

This is not a ranking of investment attractiveness and not investment advice. It is a workflow prioritization tool.

## Inputs

Required CSV column:

```csv
ticker
```

Optional columns:

```csv
exchange,idea_source,priority,notes
```

Optional artifact directories:

- `--audit-dir`: directory containing `audit_summary` JSON artifacts.
- `--business-risk-dir`: directory containing `business_risk_package` JSON artifacts.

## CLI

```bash
PYTHONPATH=src python -m sws_engine.cli audit-watchlist \
  --watchlist data/watchlists/core.csv \
  --audit-dir out/audit \
  --business-risk-dir out/business_risks \
  --output out/watchlist_audit/core
```

## Rules

A ticker is not dropped when an artifact is missing. It is classified as `Data Limited` with reason code `WATCHLIST_AUDIT_ARTIFACT_MISSING`.

A ticker with `model_applicability.status=DEGRADED` or restricted `allowed_score_usage` is classified as `Needs Different Model`.

A ticker with high/unknown conclusion risk or business-risk red flags requires manual review.

## Preserved governance

- No canonical `output_schema.json` changes.
- No changes to `checks/`, `valuation/`, `growth/` or `portfolio/`.
- No BUY/SELL/HOLD language.
- UNKNOWN remains visible.
- yfinance/provider degradation remains visible.
- Report footer keeps attribution and not-investment-advice language.
