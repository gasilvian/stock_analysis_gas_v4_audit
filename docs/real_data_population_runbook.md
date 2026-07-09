# Real Data Population Runbook v3.1

This runbook closes the gap between the construction/demo build and an internal daily run with real or curated inputs.

## Scope

The product can use live `yfinance` data only through `provider_profile=yfinance_pragmatic`. This is not a faithful Simply Wall St data feed. Missing or approximate fields must remain visible through `UNKNOWN`, `source_quality`, `input_lineage` and warnings.

## Required gates

Before a daily internal run:

```bash
python -m sws_engine.cli legal-scope-report --scope config/legal_scope.yaml
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness --scope config/legal_scope.yaml --registry config/source_registry.yaml
```

For external or commercial access, set `legal_review_completed: true` only after separate legal review. The default package is internal/non-commercial.

## Populate live yfinance snapshots and payloads

```bash
python -m sws_engine.cli populate-real-sources \
  --watchlist data/watchlists/watchlist_real_template.csv \
  --out-dir data/real_sources \
  --valuation-date 2026-07-08 \
  --refresh
```

Outputs:

- `data/real_sources/snapshots/<TICKER>_snapshot.json`
- `data/real_sources/payloads/<TICKER>_payload.json`
- `data/real_sources/manifests/real_source_population_*.json`

## Curated universe

Replace templates with curated files:

- `data/real_sources/universe/universe_US_curated.csv`
- `data/real_sources/universe/universe_BVB_curated.csv`

Validate:

```bash
python -m sws_engine.cli validate-universe \
  --universe data/real_sources/universe/universe_US_curated.csv \
  --output out/universe_US_coverage.json
```

## Rates and FX

Replace templates with versioned source exports:

- `data/real_sources/rates/bond_yields_10y_curated.csv`
- `data/real_sources/rates/erp_curated.json`
- `data/real_sources/fx/fx_eod_curated.csv`

Validate:

```bash
python -m sws_engine.cli rates-report \
  --bond-csv data/real_sources/rates/bond_yields_10y_curated.csv \
  --erp-json data/real_sources/rates/erp_curated.json \
  --fx-csv data/real_sources/fx/fx_eod_curated.csv
```

## Legal scope

Default:

```yaml
usage_scope: internal_personal_educational
external_access_enabled: false
commercial_use_enabled: false
legal_review_completed: false
```

This means the release is suitable for internal/personal/educational prototype use only. Any external/commercial use is blocked by the legal-scope gate until legal review is recorded.

## Non-negotiable interpretation rules

- Do not hide `UNKNOWN`.
- Do not normalize scores by known checks.
- Do not treat yfinance as a faithful SWS feed.
- Do not calculate exact PB without explicit intangible assets.
- Do not invent analyst estimates, FCF estimates, AFFO/FFO/NAV, or bank NPL/deposit/charge-off fields.
