# Audit Methodology v0.1

The audit layer consumes an already validated SWS Snowflake Engine v3.1 output and produces
auxiliary research-audit artifacts. It does not change the base engine, formulas, checks, or
`schemas/output_schema.json`.

## Data Confidence v1

`data_confidence.py` calculates a transparent confidence label from existing output metadata:

- `coverage_pct` from axis scores.
- `source_quality` mix from checks.
- UNKNOWN check count and UNKNOWN clusters.
- provider degradation, especially `yfinance_pragmatic`.
- critical missing inputs inferred from UNKNOWN checks and reason codes.

Quality weights in v0.1:

| source_quality | weight |
|---|---:|
| exact | 1.00 |
| exact_or_approximation | 0.85 |
| approximation | 0.60 |
| approximation_or_missing | 0.40 |
| assumption | 0.30 |
| missing | 0.00 |

The display levels are `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`.
For compatibility with the v4.0 master plan, the output also exposes `confidence_grade` A-E.
`yfinance_pragmatic` caps high confidence to a medium-equivalent display in P0.1.

## Critical Missing Inputs Map

UNKNOWN checks are grouped by `reason_code`, and critical missing inputs are inferred from:

- check name;
- check `reason_code`;
- check `inputs`;
- check `input_lineage`.

The map is intentionally conservative. If a precise missing field cannot be inferred,
`unknown_input` is returned rather than inventing a field.

## Model Applicability v1

`model_applicability.py` returns:

- `STANDARD_OK`;
- `DEGRADED`;
- `NOT_APPLICABLE`;
- `UNKNOWN`.

It also returns `allowed_score_usage`:

- `rankable`;
- `display_only`;
- `audit_only`;
- `do_not_compare`.

Banks, insurance companies, REITs, funds/ETFs, cyclicals, utilities, and loss-making companies
are not treated as generic standard industrial equities without warning.

## Conclusion Risk v1

`conclusion_risk.py` is a deterministic guardrail, not an investment recommendation. It uses
max/guardrail logic over:

- data confidence;
- model applicability;
- UNKNOWN check count;
- provider degradation;
- allowed score usage.

It returns `LOW`, `MEDIUM`, `HIGH`, or `UNKNOWN`, with explicit drivers and manual review
items.

## Audit Summary and Report

`audit_summary.py` aggregates the P0.1 components into `audit_summary.schema.json`.
`audit_report.py` renders Markdown with mandatory sections:

- Audit summary.
- Score and coverage.
- What we don't know.
- Source quality mix.
- Conclusion risk drivers.
- Manual review items.
- Warnings.
- Attribution and not-investment-advice footer.

## UNKNOWN preservation

Any P0.1 artifact must preserve UNKNOWN visibility. A report that does not surface UNKNOWN
information must fail the governance gate.

## P0.2 extension — Data Confidence and Model Applicability hardening

Sprint P0.2 keeps the P0.1 contract intact and adds auxiliary governance inputs:

- `config/audit_policies.yaml` controls audit-layer thresholds, source-quality weights, provider caps and TTL policies. It is deliberately separate from `config/assumptions.yaml`; it does not affect valuation, growth, checks or portfolio formulas.
- `config/source_registry.yaml` now carries field-level audit metadata: `tier`, `license_status`, `ttl_days`, `allowed_fields` / `field_quality_caps`, and `field_rules` for critical fields.
- Data Confidence now reports `source_tier_mix`, `field_quality_details`, `stale_fields`, `field_lineage_score`, and `policy_version` when field lineage is present.
- Model Applicability can optionally use `data/real_sources/reference/identifier_master.csv`; missing identifier master remains non-blocking and degrades to heuristic/manual review.
- API now exposes component endpoints: `GET /companies/{ticker}/data-confidence` and `GET /companies/{ticker}/model-applicability`.

P0.2 still does not implement SEC, FRED, ERP, sensitivity, reverse DCF, red flags, thesis tracker, decision journal, portfolio audit or memo generator.
