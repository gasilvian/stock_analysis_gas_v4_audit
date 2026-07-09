# v4.0 P0.4 — Rates, ERP and Identifier Master Foundation

This sprint implements the next controlled foundation slice after SEC-first statements.
It does not claim production readiness and does not fetch live internet data in CI.

## Scope

Implemented components:

- Curated 10Y bond-yield CSV builder from local FRED/Treasury-style exports.
- ERP curated JSON validation with review lifecycle and expiry.
- Identifier Master CSV builder from curated universe + optional SEC CIK map.
- Source Registry additions for FRED/Treasury, Damodaran ERP, Identifier Master, ECB/BNR FX references.
- CLI commands:
  - `refresh-rates-fred`
  - `validate-erp-curated`
  - `enrich-identifiers`

## Non-goals

This sprint does not implement:

- Live FRED/Treasury API fetching as CI requirement.
- ERP web scraping or automatic ERP download.
- Production-readiness PASS.
- SEC Frames averages builder.
- FX loaders for ECB/BNR.
- OpenFIGI/GLEIF live enrichment.
- CUSIP derivation or scraping.
- Sensitivity, reverse DCF, red flags, memo generator.

## Curated rates workflow

Input can be a FRED-style export:

```csv
DATE,DGS10
2026-07-06,4.15
2026-07-07,4.12
```

Command:

```bash
PYTHONPATH=src python -m sws_engine.cli refresh-rates-fred \
  --input-csv data/operator_exports/fred_DGS10.csv \
  --output data/real_sources/rates/bond_yields_10y_curated.csv \
  --country US \
  --currency USD \
  --series-id DGS10 \
  --review-status operator_review_required \
  --report out/rates/fred_DGS10_refresh_report.json
```

Output remains compatible with the existing rates engine because it preserves
`country,date,yield_10y` and adds lineage/review columns.

## ERP workflow

ERP is not objective data. It is a curated market assumption and requires review.

Required fields:

```json
{
  "source": "damodaran_manual_curated",
  "as_of": "YYYY-MM-DD",
  "review_status": "reviewed",
  "reviewed_by": "operator",
  "review_date": "YYYY-MM-DD",
  "expires_at": "YYYY-MM-DD",
  "sensitivity_required": true,
  "countries": {
    "US": {"erp": 0.0433, "country_risk_premium": 0.0}
  }
}
```

Validation:

```bash
PYTHONPATH=src python -m sws_engine.cli validate-erp-curated \
  --input data/real_sources/rates/erp_curated.json \
  --require-reviewed \
  --output out/rates/erp_validation_report.json
```

Draft or expired ERP remains `NOT_READY`.

## Identifier Master workflow

Command:

```bash
PYTHONPATH=src python -m sws_engine.cli enrich-identifiers \
  --input data/real_sources/universe/universe_US_curated.csv \
  --cik-map data/real_sources/reference/sec_company_tickers.json \
  --output data/real_sources/reference/identifier_master.csv \
  --valuation-date YYYY-MM-DD \
  --report out/reference/identifier_master_report.json
```

Rules:

- CIK can be added from SEC `company_tickers`.
- CUSIP/ISIN/FIGI/LEI are optional/manual unless legitimately provided.
- Missing CIK is reported as a warning, not inferred.
- Duplicate `(ticker, exchange)` fails validation.
- ETF/fund securities are classified as `fund_etf_excluded`.

## Governance

Preserved controls:

- `output_schema.json` not modified.
- `checks/`, `valuation/`, `growth/`, `portfolio/` not modified.
- UNKNOWN policy preserved.
- yfinance remains pragmatic/degraded.
- Production readiness remains `NOT_READY` until real curated files are populated and reviewed.
