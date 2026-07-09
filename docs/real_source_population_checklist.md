# Real Source Population Checklist — SWS Snowflake Engine v3.1

This checklist is the controlled handoff from a technically complete prototype to an internal daily run backed by real or curated source files.

It does **not** mark the product as production-ready by itself. Production readiness only passes when the files referenced by `config/source_registry.yaml` exist at their target paths and do not contain `template`, `sample`, `synthetic`, `demo`, or similar markers.

## 1. Scope and legal gate

Before populating real sources, confirm the intended use:

```bash
python -m sws_engine.cli legal-scope-report --scope config/legal_scope.yaml
```

Allowed without legal review:

- personal use;
- educational use;
- internal non-commercial evaluation.

Blocked without explicit review:

- external user access;
- paid access;
- client consulting deliverables;
- commercial deployment.

The product is not investment advice and is not the live Simply Wall St platform.

## 2. Source readiness baseline

Run:

```bash
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness --scope config/legal_scope.yaml --registry config/source_registry.yaml
```

Expected status before real population:

```text
NOT_READY
```

That is correct. It means templates and placeholders have not been mistaken for real curated source data.

## 3. Populate the US universe

Target file:

```text
data/real_sources/universe/universe_US_curated.csv
```

Minimum columns expected by the workflow:

```csv
ticker,exchange,company_name,country,region,market,industry,sector,currency,include,exclusion_reason,source,source_as_of,source_url_or_reference,curated_by,curated_at
```

Rules:

- Use real listed securities only.
- Exclude funds, ETFs, duplicate listings, DRs, non-operating shells, and instruments with unreliable coverage.
- Keep the `source` and `source_as_of` fields populated.
- Do not copy sample files into this target path unless you replace all sample/template markers and fill genuine source metadata.

Validation:

```bash
python -m sws_engine.cli validate-universe \
  --universe data/real_sources/universe/universe_US_curated.csv \
  --output out/universe_US_coverage.json
```

## 4. Populate 10Y government bond yields

Target file:

```text
data/real_sources/rates/bond_yields_10y_curated.csv
```

Minimum columns:

```csv
country,date,yield_10y,source,source_as_of,source_url_or_reference,curated_by,curated_at
```

Rules:

- Use official or curated exports only, for example FRED, treasury, central bank, or documented manual export.
- Keep dates ISO formatted: `YYYY-MM-DD`.
- Use decimal rates consistently if the loader expects decimal rates, or document percentage units clearly in the metadata/source note.
- Do not fill missing history by interpolation unless the method is explicitly documented and marked as assumption/approximation.

Validation together with ERP and FX:

```bash
python -m sws_engine.cli rates-report \
  --bond-csv data/real_sources/rates/bond_yields_10y_curated.csv \
  --erp-json data/real_sources/rates/erp_curated.json \
  --fx-csv data/real_sources/fx/fx_eod_curated.csv
```

## 5. Populate ERP table

Target file:

```text
data/real_sources/rates/erp_curated.json
```

Recommended structure:

```json
{
  "metadata": {
    "source": "operator_curated_export",
    "source_as_of": "YYYY-MM-DD",
    "curated_by": "name-or-role",
    "curated_at": "YYYY-MM-DD",
    "unit": "decimal",
    "notes": "No sample/template markers. Replace with real documented source."
  },
  "countries": {
    "US": {
      "equity_risk_premium": 0.045,
      "source": "documented real source",
      "source_as_of": "YYYY-MM-DD"
    }
  }
}
```

Rules:

- ERP is curated/assumption-like by nature. Keep source and date explicit.
- Do not label generated or illustrative ERP as real curated data.
- If ERP is not populated, discount-rate dependent valuation should remain degraded or UNKNOWN according to the engine rules.

## 6. Populate FX EOD when needed

Target file:

```text
data/real_sources/fx/fx_eod_curated.csv
```

Minimum columns:

```csv
date,pair,rate,source,source_as_of,source_url_or_reference,curated_by,curated_at
```

Required for:

- multi-currency portfolios;
- companies whose reporting currency and portfolio/base currency differ;
- portfolio attribution with price gain versus FX gain.

## 7. Populate live yfinance snapshots and payloads

This step populates pragmatic yfinance snapshots and mapped payloads. It does not convert yfinance into a faithful SWS source.

```bash
python -m sws_engine.cli populate-real-sources \
  --watchlist data/watchlists/watchlist_real_template.csv \
  --out-dir data/real_sources \
  --valuation-date YYYY-MM-DD \
  --refresh
```

Outputs:

```text
data/real_sources/snapshots/
data/real_sources/payloads/
data/real_sources/manifests/
```

Expected warnings are acceptable when yfinance lacks analyst estimates, FCF forward estimates, REIT AFFO/FFO/NAV, or bank-specific NPL/deposit/charge-off fields.

## 8. Manual overrides to reduce UNKNOWN

Use the templates in `templates/` to supply fields that yfinance cannot provide robustly:

- analyst estimates with analyst count;
- FCF forward estimates;
- AFFO/FFO/NAV for REITs;
- NPL, deposits, allowances, charge-offs for banks;
- industry averages when universe coverage is insufficient.

Commands:

```bash
python -m sws_engine.cli validate-input -i data/real_sources/payloads/AAPL_payload.json --report out/AAPL_input_dry_run.md
python -m sws_engine.cli merge-overrides --base data/real_sources/payloads/AAPL_payload.json --override templates/manual_override_template.json --output data/real_sources/payloads/AAPL_curated_payload.json
```

## 9. Final readiness gate

After population, run:

```bash
python -m sws_engine.cli production-readiness \
  --scope config/legal_scope.yaml \
  --registry config/source_registry.yaml \
  --require-production
```

The gate must stay `NOT_READY` if any required source:

- is missing;
- points to a template path;
- contains sample/template/synthetic markers;
- lacks legal scope clearance for the intended external/commercial use.

## 10. Evidence to keep

For each daily production-like run, preserve:

- source registry report;
- production-readiness report;
- universe validation report;
- rates/FX report;
- batch run report;
- validation snapshot;
- assumptions hash;
- provider version metadata.

## 11. Acceptance wording

Use this wording until all real sources and legal scope are cleared:

```text
technical product complete; production use requires curated real-source population and legal scope clearance
```
