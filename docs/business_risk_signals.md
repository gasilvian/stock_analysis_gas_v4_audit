# Business Risk Signals — v4.0 P0.7

P0.7 adds an auxiliary audit layer for red flags, accounting quality and capital allocation. It does **not** modify the canonical v3.1 `output_schema.json`, the 30 Snowflake checks, valuation, growth, scoring or portfolio logic.

## Scope

Implemented module:

```text
src/sws_engine/audit/risk_signals.py
```

Implemented CLI:

```bash
PYTHONPATH=src python -m sws_engine.cli business-risk-company \
  --input tests/fixtures/business_risk/risk_payload.json \
  --output out/business_risk_ci
```

Implemented API endpoint:

```text
GET /companies/{ticker}/business-risks
```

Implemented schema:

```text
schemas/aux/business_risk_package.schema.json
```

## Governance

The module is additive. It consumes supplied payloads, persisted input snapshots and/or persisted outputs. It does not fetch external data and does not infer missing values. Missing values return `UNKNOWN` with `BUSINESS_RISK_INPUTS_MISSING`.

Each signal carries:

```text
status
reason_code
source_quality
source_class
input_lineage
```

This preserves the v4 audit principle that every displayed value has a data passport.

## Red flag checks in P0.7

P0.7 implements the first deterministic red-flag set:

```text
NEGATIVE_OPERATING_CASH_FLOW
NEGATIVE_FREE_CASH_FLOW
EARNINGS_CASH_FLOW_DIVERGENCE
DIVIDEND_NOT_COVERED_BY_FCF
HIGH_INTANGIBLES_TO_ASSETS
ELEVATED_NET_DEBT_TO_EQUITY
SHARE_DILUTION_ABOVE_10PCT
ENGINE_UNKNOWN_CHECKS_PRESENT
```

Triggered flags are placed in `red_flags`. All evaluated PASS/FAIL/UNKNOWN signals are preserved in `red_flag_checks`.

## Accounting quality metrics

P0.7 implements:

```text
ACCRUALS_RATIO
FCF_CONVERSION
GROSS_MARGIN_VARIABILITY
```

The output grade is:

```text
STRONG / NORMAL / WATCH / WEAK / UNKNOWN
```

The grade is not a Snowflake score and must not be ranked as company quality without source-quality review.

## Capital allocation metrics

P0.7 implements:

```text
DIVIDENDS_TO_FCF
BUYBACKS_TO_FCF
CAPEX_INTENSITY
SHARE_COUNT_GROWTH
```

The assessment is:

```text
BALANCED / WATCH / UNKNOWN
```

## Limitations

P0.7 is a foundation slice. It does not implement full forensic accounting, sector-specific red flags, bank-specific credit quality, REIT AFFO/FFO/NAV analysis, investment memo generation or portfolio audit.

## Not investment advice

This module produces audit signals only. It does not produce BUY, SELL or HOLD recommendations.
