# Validation Report — v4.0 P0.4 Rates, ERP and Identifier Master Foundation

## Scope implemented

Implemented the next controlled sprint after P0.3: **Rates / ERP / Macro Assumption and Identifier Master Foundation**.

Implemented:

- `src/sws_engine/rates/curated.py` for reviewed-aware curated rates and ERP workflows.
- `src/sws_engine/reference/identifier_master.py` for Identifier Master generation and validation.
- CLI `refresh-rates-fred` for converting local FRED/Treasury-style 10Y exports into engine-compatible curated bond CSVs.
- CLI `validate-erp-curated` for ERP review lifecycle validation.
- CLI `enrich-identifiers` for building Identifier Master CSVs from curated universes and optional SEC CIK maps.
- `config/source_registry.yaml` extensions for:
  - `fred_dgs10_curated_export`
  - `treasury_fiscaldata_rates`
  - `damodaran_erp_manual_curated`
  - `identifier_master_curated`
  - `ecb_fx_reference_rates`
  - `bnr_fx_reference_rates`
- Field rules for `CIK`, `security_type`, `company_type`, `fx_rate`, and expanded allowed sources for risk-free rates and ERP.
- `docs/rates_erp_identifier_master.md`.
- Offline fixtures for FRED-style DGS10 exports, reviewed/draft ERP JSON, SEC company tickers, and curated universe.
- Tests for curated rates conversion, reviewed/draft ERP lifecycle, Identifier Master creation/validation, and P0.4 CLIs.

## Explicitly not implemented

This sprint does **not** implement:

- Live FRED/Treasury API fetching as a CI requirement.
- ERP web scraping or automatic ERP download.
- Production-readiness PASS.
- SEC Frames API averages builder.
- FX loaders for ECB/BNR.
- OpenFIGI / GLEIF live enrichment.
- CUSIP derivation or scraping.
- Full source conflict detector runtime.
- sensitivity matrix.
- reverse DCF.
- red flag engine.
- accounting quality.
- capital allocation.
- watchlist audit.
- thesis tracker.
- decision journal.
- portfolio audit.
- memo generator.
- complex dashboard pages.

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved: missing or draft curated data remains `NOT_READY` / review-required, not silently accepted.
- ERP remains a curated assumption (`source_quality=assumption`, `source_class=E2`) and not objective data.
- CUSIP/ISIN/FIGI/LEI remain optional/manual; the Identifier Master does not infer licensed identifiers.
- Production readiness remains `NOT_READY` until real curated source files are populated and reviewed.

## CLI smoke runs

```bash
PYTHONPATH=src python -m sws_engine.cli refresh-rates-fred \
  --input-csv tests/fixtures/rates/fred_DGS10.csv \
  --output out/p04_ci/bond_yields_10y_curated.csv \
  --report out/p04_ci/rates_report.json
```

Result:

```text
PASS_WITH_LIMITATIONS; observations_written=3; review_status=operator_review_required
```

```bash
PYTHONPATH=src python -m sws_engine.cli validate-erp-curated \
  --input tests/fixtures/rates/erp_curated_reviewed.json \
  --require-reviewed \
  --output out/p04_ci/erp_validation_report.json
```

Result:

```text
PASS; countries_count=2; review_status=reviewed
```

```bash
PYTHONPATH=src python -m sws_engine.cli enrich-identifiers \
  --input tests/fixtures/reference/universe_us_minimal.csv \
  --cik-map tests/fixtures/reference/sec_company_tickers.json \
  --output out/p04_ci/identifier_master.csv \
  --valuation-date 2026-07-09 \
  --report out/p04_ci/identifier_report.json
```

Result:

```text
PASS_WITH_LIMITATIONS; rows_written=4; issues_count=1
```

The expected Identifier Master warning is for a ticker without CIK in the fixture map; it is not inferred.

## Tests run

The full all-in-one pytest command was not used as the final reported command because it hit the sandbox wall-clock timeout in this environment. Equivalent coverage was run in segmented offline groups:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/averages_real tests/ci tests/contract tests/dashboard \
  tests/data_layer tests/deploy tests/docs tests/gold tests/governance tests/integration \
  tests/manual tests/ops tests/persistence tests/portfolio tests/providers tests/synthetic -q
```

Result:

```text
152 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/rates tests/reference tests/sec tests/sources -q
```

Result:

```text
19 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/e2e tests/live -q
```

Result:

```text
2 skipped
```

Total segmented coverage:

```text
171 passed, 2 skipped
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
PYTHONPATH=src python scripts/ci/check_audit_unknown_preserved.py out/audit_ci
PYTHONPATH=src python scripts/ci/check_source_registry_field_rules.py
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation and source-registry field rules.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.4 uses local official/operator exports; live FRED/Treasury fetching is not a CI requirement yet.
2. ERP is validated as a manual curated assumption and still requires operator review and expiry management.
3. Identifier Master is generated from curated universe + optional SEC CIK map; no OpenFIGI/GLEIF live enrichment is implemented.
4. ECB/BNR FX sources are registered structurally, but FX loaders are future work.
5. Production readiness remains blocked by curated source population and review, by design.
