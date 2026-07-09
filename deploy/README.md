# Deployment and operations — Phase 8 baseline

This is a production-like internal deployment scaffold. It does not make the model commercially validated and it does not remove the legal/model-risk limitations.

## Local container run

```bash
cp .env.example .env
# optionally edit SWS_API_AUTH_ENABLED/SWS_API_KEY
docker compose up --build api dashboard
```

Open:

- API: http://127.0.0.1:8000/docs
- Dashboard: http://127.0.0.1:8501

## Volumes

`docker-compose.yml` defines persistent volumes:

- `sws_data` for SQLite, input/output data and real-data templates
- `sws_cache` for provider cache
- `sws_snapshots` for validation snapshots

The JSON output remains the source of truth; extracted DB columns are query indexes only.

## Operational jobs

EOD refresh can be run through the ops profile:

```bash
docker compose --profile ops run --rm eod-refresh
```

Backup:

```bash
BACKUP_DIR=backups ./ops/backup.sh
```

Monitoring:

```bash
API_URL=http://127.0.0.1:8000 ./ops/monitoring.sh
```

## Security baseline

Use API key auth for any shared environment:

```bash
SWS_API_AUTH_ENABLED=true
SWS_API_KEY=<long-random-secret>
```

Do not expose the dashboard publicly without a legal/security review.

## Remaining limitations

- Live yfinance is pragmatic/degraded, not a faithful SWS institutional data source.
- Real market/industry universes, rates and FX files must be populated and governed.
- This is not investment advice and not the live Simply Wall St model.

## Dashboard interpretation controls

The dashboard and API must keep `UNKNOWN` visible and must display `coverage_pct` alongside any score. Do not treat low coverage as equivalent to a fully evaluated high score.

## CI/deploy final validation notes

The CI workflow installs the package with `dev`, `api`, `dashboard`, `live`, `ci` and `e2e` extras, but normal CI remains offline: live and browser E2E tests are opt-in via environment variables.

The monitoring script reads the latest `logs/eod_refresh_*.json` file and emits an alert when either batch failures or live snapshot failures exceed 20% of processed rows. This mirrors the operational threshold from the product plan and is intentionally separate from model scoring.

Expected operational commands:

```bash
python -m pip install -e ".[dev,api,dashboard,live,ci,e2e]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/ci/validate_demo_outputs.py
python scripts/ci/check_no_score_normalized.py
python scripts/ci/check_attribution_footer.py
python scripts/ci/check_real_source_population_workflow.py
BACKUP_DIR=backups ./ops/backup.sh
API_URL=http://127.0.0.1:8000 ./ops/monitoring.sh
```
