# Validation Report — SWS Snowflake Engine v3.1 CI/Deploy Final

## Verdict

**PASS WITH LIMITATIONS**

Status wording:

> technical product complete; production use requires curated real-source population and legal scope clearance

## Scope checked

This validation covers final CI, deployment scaffold and operational runbook controls. It does **not** change model formulas, checks, `output_schema.json`, provider-degradation policy, dashboard interpretation rules or production source truthfulness.

## CI readiness

Implemented/validated controls:

- `.github/workflows/ci.yml`
  - installs package with dev/API/dashboard/live/CI/E2E extras;
  - runs offline pytest;
  - runs ruff lint;
  - validates demo output schema;
  - runs no-`score_normalized` governance gate;
  - runs dashboard attribution/footer gate;
  - runs real-source population honesty gate;
  - emits legal/source/production-readiness reports.
- `.github/workflows/release.yml`
  - runs gold/portfolio/contract tests;
  - runs schema and governance gates;
  - cleans local artifacts;
  - publishes a release archive artifact.

## Deployment scaffold readiness

Implemented/validated controls:

- `Dockerfile` for API/engine container.
- `dashboard.Dockerfile` for Streamlit dashboard container.
- `docker-compose.yml` with API, dashboard and opt-in EOD refresh service.
- Persistent volumes for data/cache/snapshots/logs through compose and bind mounts.
- `.env.example` for API, dashboard, ops and optional-test settings.
- `deploy/README.md` and `deploy/production_checklist.md` updated.

## Ops readiness

Implemented/validated controls:

- `ops/backup.sh` archives DB, validation snapshots, config and schemas.
- `ops/monitoring.py` and `ops/monitoring.sh` write monitoring evidence to `logs/`.
- Monitoring now emits alerts when batch or live snapshot failures exceed 20%.
- `ops/eod_refresh_real.sh` runs the EOD refresh orchestration with configurable watchlist/universe/provider mode.
- `ops/security.md` documents the API key baseline and public exposure restrictions.

## Test commands

Normal offline validation:

```bash
python -m pip install -e ".[dev,api,dashboard,live,ci,e2e]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/ci/validate_demo_outputs.py
python scripts/ci/check_no_score_normalized.py
python scripts/ci/check_attribution_footer.py
python scripts/ci/check_real_source_population_workflow.py
python -m ruff check src dashboard tests scripts
```

Operational readiness commands:

```bash
python -m sws_engine.cli legal-scope-report --scope config/legal_scope.yaml
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness --scope config/legal_scope.yaml --registry config/source_registry.yaml
```

API/dashboard smoke:

```bash
uvicorn sws_engine.api.app:app --host 127.0.0.1 --port 8000
streamlit run dashboard/app.py
```

Docker smoke:

```bash
cp .env.example .env
docker compose up --build api dashboard
```

## Skipped optional tests

These remain skipped in normal/offline CI:

```bash
SWS_RUN_LIVE_TESTS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -m live -q
SWS_RUN_E2E_TESTS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -m e2e -q
```

They are intentionally opt-in because they require network and/or browser/runtime services.

## Evidence from this validation run

Executed in the audit environment:

- `PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`
  - result: `122 passed, 2 skipped`
- `PYTHONPATH=src python scripts/ci/validate_demo_outputs.py`
  - result: OK
- `PYTHONPATH=src python scripts/ci/check_no_score_normalized.py`
  - result: OK
- `PYTHONPATH=src python scripts/ci/check_attribution_footer.py`
  - result: OK
- `PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py`
  - result: OK, production readiness remains NOT_READY until real curated sources are populated
- `python -m ruff check src dashboard tests scripts`
  - result: OK after installing CI extra

## Remaining limitations

- Real market/universe/rate/ERP/FX source files are not bundled as production-curated data.
- `production-readiness --require-production` must remain NOT_READY until operator-supplied real source files are populated and pass registry checks.
- Live yfinance is `yfinance_pragmatic`, not a faithful Simply Wall St institutional provider.
- Browser E2E and live tests are opt-in and were not run by default.
- Docker compose was not executed in this validation environment; run the smoke command in the target environment.
- External/commercial deployment requires legal scope clearance and security review.

## Model-risk controls preserved

- No model formulas changed.
- `output_schema.json` unchanged.
- `UNKNOWN`, warnings and lineage are preserved.
- No real data was fabricated.
- Dashboard must keep coverage and UNKNOWN visible.
- `score_normalized` is not exposed as a runtime/primary score.
- Legal/source readiness gates prevent false production claims.
