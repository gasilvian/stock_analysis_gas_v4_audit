# Real Source Examples — Samples Only

This folder contains **sample shapes** for operator-supplied real-source files.

These files are not curated production data and must not be copied into `data/real_sources/` unchanged. They intentionally include `sample_only` markers so the readiness gate can detect accidental use of samples as production inputs.

## Target production paths

| Source | Real target path |
|---|---|
| US universe | `data/real_sources/universe/universe_US_curated.csv` |
| 10Y bond yields | `data/real_sources/rates/bond_yields_10y_curated.csv` |
| ERP table | `data/real_sources/rates/erp_curated.json` |
| FX EOD | `data/real_sources/fx/fx_eod_curated.csv` |

## Rules

- Replace all sample rows with real documented source data.
- Remove `sample_only`, `template`, and `synthetic` markers before using a file as a curated real source.
- Keep source, source date, curator and curation timestamp populated.
- Run production readiness after population.

## Validation

```bash
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness --scope config/legal_scope.yaml --registry config/source_registry.yaml --require-production
```

Expected status while these are still only samples:

```text
NOT_READY
```
