# Validation Report — Real Source Population Readiness

## Scope

This report covers the final P1 gap after the GitHub audit: operator population of real or curated source files.

The following model/runtime logic was intentionally not changed:

- engine checks;
- valuation formulas;
- `output_schema.json`;
- API output contract;
- dashboard rendering rules;
- UNKNOWN and provider degradation policy.

## Deliverables added

- `docs/real_source_population_checklist.md`
- `examples/real_sources/README.md`
- `examples/real_sources/sample_universe_US.csv`
- `examples/real_sources/sample_bond_yields_10y.csv`
- `examples/real_sources/sample_erp.json`
- `examples/real_sources/sample_fx_eod.csv`
- `scripts/ci/check_real_source_population_workflow.py`
- tests for source marker detection and workflow guard
- README section: Real Source Population — operator checklist

## Control enhancement

`src/sws_engine/sources/real_sources.py` now checks not only the target path/status but also the beginning of each target file for sample/template/synthetic markers such as:

- `sample_only`
- `template`
- `synthetic`
- `not real data`
- `demo_fixture`
- `example only`

This prevents accidental production readiness when an operator copies sample files into `data/real_sources/` without replacing them with genuine documented sources.

## Current readiness status

Expected current state:

```text
NOT_READY
```

Reason: real curated files are not bundled with the repository. The operator must populate:

- `data/real_sources/universe/universe_US_curated.csv`
- `data/real_sources/rates/bond_yields_10y_curated.csv`
- `data/real_sources/rates/erp_curated.json`
- optionally `data/real_sources/fx/fx_eod_curated.csv` for multi-currency use

## Commands to run

```bash
python -m pip install -e ".[dev,api,dashboard,live,ci,e2e]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/ci/check_real_source_population_workflow.py
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness --scope config/legal_scope.yaml --registry config/source_registry.yaml --require-production
```

## Verdict

```text
PASS WITH LIMITATIONS
```

The project is technically complete. Production use requires curated real-source population and legal scope clearance.
