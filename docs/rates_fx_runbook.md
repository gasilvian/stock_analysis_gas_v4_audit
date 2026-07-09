# Rates and FX runbook

Operational use needs versioned, documented sources:

- 10Y government bond series by country, used to compute 5-year average.
- Country equity risk premium table.
- EOD/reference FX table.

Inspect source files:

```bash
python -m sws_engine.cli rates-report \
  --bond-csv data/rates/bond_yields_10y.csv \
  --erp-json data/rates/erp.json \
  --fx-csv data/fx/fx_eod.csv
```

Templates:

- `data/rates/bond_yields_10y_real_template.csv`
- `data/rates/erp_real_template.json`
- `data/fx/fx_eod_real_template.csv`

Synthetic files are acceptable for construction/testing only. For real operation,
export/version the source files and keep them immutable for each run date.
