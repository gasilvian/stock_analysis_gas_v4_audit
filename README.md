# SWS Snowflake Engine v3.1 — Phase 4 Candidate Build

Controlled, contract-compliant implementation of the **public GitHub Simply Wall St methodology** — both models:

- **Company-Analysis-Model** (Snowflake: 30 checks, valuation, growth engine)
- **Portfolio-Analysis-Model** (returns, AYI/CAGR, FX, corporate actions, portfolio Snowflake)

> **Not investment advice.** Does not reproduce the current/live Simply Wall St platform. Source methodology is CC BY-NC-SA 4.0 — attribution preserved (see model pack `legal/`); commercial use requires legal review.


## Release-candidate status

This archive is a **Phase 4 candidate build**. It includes the company engine, portfolio engine, synthetic/no-network data layer, SQLite persistence and batch orchestration. It is suitable for controlled prototype/demo validation, not production deployment.

Current verified test status in the release-candidate environment:

```text
118 passed, 2 skipped
```

Important scope boundary: the data layer currently uses synthetic/recorded no-network construction data. The FastAPI backend layer and Streamlit dashboard prototype are present for internal development. Live market-data ingestion, Docker deployment and production validation remain future phases.

## Install & test

```bash
pip install -e ".[dev]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q  # 75 tests passing in the dashboard-step release-candidate environment
```

## Run

```bash
# Company analysis (validates against schemas/output_schema.json)
python -m sws_engine.cli company -i tests/fixtures/demo_complete_non_financial.json \
    -o out.json --report report.md --snapshot-dir validation/snapshots

# Portfolio analysis
python -m sws_engine.cli portfolio -i tests/fixtures/demo_portfolio.json \
    -o portfolio.json --report portfolio_report.md
```

Python API:

```python
from sws_engine import run_company_analysis
from sws_engine.portfolio.portfolio_run import run_portfolio_analysis
```

## What Phase 2 added (on top of the MVP)

**Valuation engines (SPEC §4)** — `two_stage_fcf` (10-year stage 1, analyst FCF estimates, decay-curve extrapolation, Gordon terminal value, end-of-year discounting), `ddm`, `excess_returns` (Stable/Future ROE·BVE, never generic current ROE·BVE), `affo_dcf` with AFFO→FFO→NAV fallback variants. Adjusted FCF = OCF − 3y avg capex when estimates are missing. Manual `fair_value` still takes precedence (`manual_input`); strict mode still never invents values.

**Growth engine (SPEC §6)** — route A (analyst-weighted regression, cap 50 analysts, first point = actual with weight 1), route B (historical, equal weights, min 3 years), route C (fundamentals/ROE convergence to industry median with beginning-of-year equity roll-forward), with A→B→C fallback.

**Calibration discovery (E1)** — the public docs don't define how the first extrapolated FCF year is seeded. Calibrated on the AMZN example: first `(r − g) = decay² × (avg analyst YoY − g)`, then `r_t − g = 0.7·(r_{t−1} − g)`. Reproduces the documented 14.77%→5.62% path within 0.05pp. Registered as `dcf_extrapolation_seed_policy` (configurable) in `config/assumptions.yaml`.

**Health variants (SPEC §5.4–5.6)** — financial institutions HF1–HF6; loss-making companies (current + 3y average, E2 window) switch H5/H6 to cash-runway checks. Selection is automatic per company type/profitability.

**Management module (SPEC §9)** — 5 flags (CEO comp vs cohort, pay↑/EPS↓, management/board tenure, insider net selling), emitted only with `include_management: true`, never counted in Snowflake scores (tested).

**Portfolio engine (SPEC §8)** — watchlist/holdings/portfolio types with synthetic buys; money-weighted returns (`Gain`, `Total_Return`, `AYI`, `CAGR`, CAGR suppressed when AYI < 1); buy duration measured to valuation date even for lots later sold (E1 policy); ACT/365.25; FX price-vs-currency gain split; splits round fractional shares up; dividend reinvestment at zero cost; weighted Snowflake aggregation with ETF exclusion, outlier caps and the contributor-sum invariant.

**Reporting & CLI** — markdown reports for company and portfolio, `sws-engine` console entry point, validation snapshots per run.

## Gold tests (all passing, public-example calibrated)

| Test | Expected | Tolerance | Status |
|---|---|---|---|
| AMZN DCF 2019 | FV $1,548 | ±0.1% FV | ✅ (−0.07%) |
| AMZN decay path | 14.77%→5.62% | 0.05pp/rate | ✅ |
| FB growth | 19.3% | ±0.5pp | ✅ (19.11%) |
| HemaCare growth | 1.85% | ±0.1pp | ✅ (1.87%) |
| Portfolio AMZN | TR 100.15%, AYI 1.93 | ±0.1pp | ✅ |
| FX split | €300 price + €100 FX | ±0.01 | ✅ |

## Phase 3 — Synthetic/no-network data layer

Everything a live provider would supply is modeled with **synthetic curated data shipped in `data/`**, marked `SYNTHETIC_CURATED_DATA` in every output. Swapping in real providers later means replacing data files, not code:

| Component | Module | Synthetic data shipped |
|---|---|---|
| Capability matrix (honest field-by-field yfinance quality) | `providers/capability_matrix.py` | — |
| Recorded-snapshot provider (drop-in shape for a future live fetcher) | `providers/recorded.py` | `data/recorded/SYN-ACME.json` (profitable dividend payer), `SYN-BURN.json` (loss-making) |
| Industry & market averages builder (medians profitable, tangible-PB average, yield percentiles P10/P25/P75, country→market fallback with `min_universe_count`) | `averages/builder.py` | `data/universe/universe_US-SYN.csv` (11 stocks + ETF/DR exclusions) |
| Rates (10Y bond 5y average, curated ERP, EOD FX) | `rates/rates.py` | `data/rates/*.csv|json`, `data/fx/fx_eod.csv` |
| Disk cache with TTL | `data/cache.py` | — |
| Payload builder (snapshot + averages + rates → engine payload) | `orchestration/payload_builder.py` | — |

```bash
# end-to-end on synthetic data:
python -m sws_engine.cli build-averages --universe data/universe/universe_US-SYN.csv \
    --market US-SYN --date 2026-07-06 --savings-rate 0.02 --cpi 0.028
python -m sws_engine.cli build-payload --snapshot data/recorded/SYN-ACME.json \
    --averages data/averages/averages_US-SYN_2026-07-06.json \
    --industry Software --country US --date 2026-07-06 -o acme_payload.json
python -m sws_engine.cli company -i acme_payload.json -o acme.json --report acme.md
```

Result on SYN-ACME: adjusted-FCF valuation (`two_stage_fcf/base`), market/industry-relative checks evaluable; SYN-BURN: automatic cash-runway health variant, valuation correctly `unknown` (strict mode). Builder warnings (synthetic data, industry fallback, ERP assumption) propagate into the final output and reports.

**To go live later:** implement a fetcher that writes the same snapshot shape into `data/recorded/`, replace the universe CSV, bond/ERP/FX files with curated real data — mapper, capability matrix, averages builder, engine and tests stay unchanged.

## Phase 4 — Persistence & batch orchestration

SQLite store (portable DDL — Postgres later means swapping the connection factory, not the SQL) in `db/schema.py` + `db/store.py`; batch runner with error isolation and bounded concurrency in `orchestration/batch.py`; scheduler docs and daily script in `ops/`.

**Tables:** `instruments`, `input_snapshots` (payload + hash), `runs` (assumptions_hash + engine_version + status PASS/FAIL/SKIPPED), `outputs` (full output JSON = source of truth, extracted score/coverage columns = query index only), `checks` (screener filtering), `averages_snapshots`, `portfolios`, `portfolio_runs`.

```bash
# daily sequence (averages -> payloads -> engine -> persist), error-isolated:
python -m sws_engine.cli batch --watchlist data/watchlists/watchlist_synthetic.csv \
    --date 2026-07-06 --db data/sws.db \
    --universe data/universe/universe_US-SYN.csv --market US-SYN \
    --savings-rate 0.02 --cpi 0.028
# -> {"PASS": [SYN-ACME, SYN-BURN], "FAIL": [], "SKIPPED": [SYN-GHOST]}

# acceptance query: score evolution with coverage, one SELECT
python -m sws_engine.cli history --db data/sws.db --ticker SYN-ACME --axis health
# screener: score AND coverage filters are both mandatory by design
python -m sws_engine.cli screener --db data/sws.db --axis health --min-score 4 --min-coverage 0.8
```

Every run records `assumptions_hash` and `engine_version` (no silent assumption changes); a failed or missing ticker never stops the batch and lands in the report as FAIL/SKIPPED with the error persisted.

## Streamlit Dashboard — Step 3

This release candidate now includes a Streamlit dashboard prototype over the FastAPI backend. The dashboard is a UI/governance layer only: it consumes FastAPI through `dashboard/api_client.py` and must not call the engine or SQLite persistence directly.

Install with dashboard extras:

```bash
pip install -e ".[dev,api,dashboard]"
```

Start the API first:

```bash
uvicorn sws_engine.api.app:app --reload
```

Start the dashboard:

```bash
streamlit run dashboard/app.py
```

Environment variables:

```text
DASHBOARD_API_URL=http://127.0.0.1:8000
DASHBOARD_API_KEY=
DASHBOARD_TIMEOUT_SECONDS=30
```

Pages available:

- **Company View** — ticker lookup, optional JSON payload run, 5-axis radar, raw score, coverage, valuation card, 30-check table, warnings, lineage and score history.
- **Portfolio View** — portfolio latest/run, weighted Snowflake, positions and returns.
- **Screener** — axis score filtering with mandatory `coverage_pct`; default `min_coverage=0.66`.
- **Run & Data Health** — API status, synthetic/no-network data-layer warning, validation status and recorded test status.
- **Assumptions & Governance** — assumptions hash, unknown scoring policy, provider profiles and E1/E2/E3 assumption visibility.

Dashboard model-risk controls:

- UNKNOWN is not hidden and is not converted to FAIL.
- No `score_normalized` is computed or displayed.
- No score is displayed without `coverage_pct`.
- `source_quality` and `source_class` are visible in the checks table.
- `yfinance_pragmatic` outputs trigger a provider-degradation banner.
- `DEMO_FIXTURE_ONLY` and `SYNTHETIC_CURATED_DATA` warnings remain visible.
- The dashboard uses the synthetic/no-network data layer in this release; live market data is not implemented.
- Not investment advice. Not the live Simply Wall St model.

Run tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Observed dashboard-step result:

```text
75 passed
```

## Provider profiles

- `sws_public_faithful_manual_inputs` — curated/manual inputs, `source_quality=exact`.
- `yfinance_pragmatic` — degradation-aware stub: SWS-required fields unavailable in yfinance are marked `missing`, dependent checks become `UNKNOWN`/`PROVIDER_LIMITATION`, warnings are always visible. Live yfinance wiring is a deliberate integration point (`providers/yfinance_pragmatic.py`), not silently approximated.

## Contract guarantees (unchanged from MVP, all tested)

Exactly 30 Snowflake checks; every check returns the full contract; missing input ⇒ UNKNOWN; D3/D4 `FAIL_BY_DEFAULT` under 10y DPS history; PB strictly from tangible book value; raw scores + coverage, never normalized; full lineage; schema validation on every run; assumptions frozen per run snapshot.

## Disclaimers

Quantitative exploratory analysis of a public historical methodology (2017–2019 documentation). Not investment advice. Not a replica of the current Simply Wall St live platform. Not validated for production or commercial deployment without legal and model-risk review.

## API FastAPI — Phase 5 Backend Layer / Pasul 2

This release candidate now includes a thin FastAPI backend layer over the existing engine and SQLite persistence. The API does **not** implement live market data and does **not** change the v3.1 output contract. Company responses return the engine output as a complete schema-valid dictionary under `output`, with API metadata in a separate wrapper.

Current verified test status after the API layer:

```text
61 passed
```

Install with API extras:

```bash
pip install -e ".[dev,api]"
```

Start the API:

```bash
uvicorn sws_engine.api.app:app --reload
# or
python -m sws_engine.cli api --host 127.0.0.1 --port 8000 --reload
```

Run tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Core endpoints:

```text
GET  /
GET  /meta/health
POST /analyze/company
POST /analyze/portfolio
GET  /companies/{ticker}/latest
GET  /companies/{ticker}/history
GET  /companies/{ticker}/checks
GET  /screener
GET  /assumptions/current
GET  /averages/{market}/{date}
GET  /portfolios/{portfolio_id}/latest
GET  /portfolios/{portfolio_id}/history
```

Example calls:

```bash
curl http://127.0.0.1:8000/meta/health

curl -X POST http://127.0.0.1:8000/analyze/company \
  -H "Content-Type: application/json" \
  -d '{"input_payload": {"ticker":"DEMO"}, "persist": false}'

curl http://127.0.0.1:8000/companies/DEMO/latest
curl "http://127.0.0.1:8000/screener?axis=value&min_score=4&min_coverage=0.8"
```

For real use, post a full payload file rather than the minimal illustrative JSON above:

```bash
python - <<'PY'
import json
from fastapi.testclient import TestClient
from sws_engine.api.app import app

payload = json.load(open("tests/fixtures/demo_complete_non_financial.json"))
client = TestClient(app)
r = client.post("/analyze/company", json={"input_payload": payload, "persist": True})
print(r.status_code)
print(r.json()["metadata"])
PY
```

Environment variables:

```text
SWS_DB_PATH              default data/sws.db
SWS_ASSUMPTIONS_PATH     default config/assumptions.yaml
SWS_SCHEMA_PATH          default schemas/output_schema.json
SWS_API_AUTH_ENABLED     default false
SWS_API_KEY              required only when auth is enabled
SWS_CORS_ORIGINS         default http://localhost:8501,http://127.0.0.1:8501
```

API key mode:

```bash
export SWS_API_AUTH_ENABLED=true
export SWS_API_KEY=secret
curl -H "X-API-Key: secret" http://127.0.0.1:8000/meta/health
```

API limitations in this candidate:

- API uses the synthetic/no-network data layer.
- Live market data integration is not implemented in this step.
- Dashboard is not implemented in this step.
- Deployment/Docker packaging is not implemented in this step.
- Not investment advice.
- Not the live Simply Wall St model.

The API intentionally keeps `UNKNOWN`, `warnings`, `source_quality`, `source_class`, `input_lineage` and `coverage_pct` visible. Screener/history responses always include coverage next to scores.

## Live Market Data — Step A

Status: `yfinance` live provider is implemented as `provider_profile=yfinance_pragmatic`. This is a pragmatic data adapter, not a faithful SWS institutional data source.

Install with live extras:

```bash
python -m pip install -e ".[dev,api,dashboard,live]"
```

Build a yfinance payload:

```bash
python -m sws_engine.cli build-payload-yfinance \
  --ticker AAPL \
  --market US \
  --industry Technology \
  --output data/inputs/AAPL_yfinance_payload.json
```

Run company analysis directly from yfinance:

```bash
python -m sws_engine.cli company-live \
  --ticker AAPL \
  --market US \
  --industry Technology \
  --output out/AAPL_output.json \
  --report out/AAPL_report.md
```

Record a yfinance raw snapshot:

```bash
python -m sws_engine.cli record-yfinance \
  --ticker AAPL \
  --output data/recorded_yfinance/AAPL_snapshot.json \
  --refresh
```

Generate a capability report:

```bash
python -m sws_engine.cli provider-capability \
  --provider yfinance \
  --ticker AAPL \
  --output out/AAPL_capability_report.md
```

Run the API:

```bash
uvicorn sws_engine.api.app:app --reload
```

Live API endpoints:

```text
POST /providers/yfinance/build-payload
POST /analyze/company-live
```

Run the dashboard:

```bash
streamlit run dashboard/app.py
```

Live provider rules and warnings:

- yfinance is not a faithful SWS/S&P Capital IQ style data source.
- Analyst estimates with forecast-year analyst counts are not invented.
- Forward FCF estimates are not invented.
- AFFO/FFO/NAV for REITs are not invented.
- Bank NPL/deposits/charge-off fields are not invented.
- Missing data produces `UNKNOWN` or documented fallback behavior.
- Provider degradation is expected and visible through warnings and source quality.
- PB exactness is preserved: tangible book value requires explicitly reported intangible assets.

Normal tests remain offline:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Optional live tests are opt-in:

```bash
SWS_RUN_LIVE_TESTS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -m live -q
```

This step still does not use the live Simply Wall St model and is not investment advice.

## Manual Overrides, Real Averages, Rates/FX and EOD Refresh — Step B/C/D/E

This release adds the operational plumbing needed after the live yfinance adapter:
manual override workflows, real-universe average building, versioned rate/FX
source inspection and EOD refresh orchestration.

### B. Manual override workflow

Validate a payload and see which checks are likely to remain `UNKNOWN`:

```bash
python -m sws_engine.cli validate-input \
  -i data/inputs/AAPL_yfinance_payload.json \
  --report out/AAPL_input_dry_run.md
```

Merge manual overrides into a yfinance payload:

```bash
python -m sws_engine.cli merge-overrides \
  --base data/inputs/AAPL_yfinance_payload.json \
  --override templates/manual_override_template.json \
  --output data/inputs/AAPL_curated_payload.json
```

Available templates:

- `templates/company_input_template.json`
- `templates/bank_input_template.json`
- `templates/reit_input_template.json`
- `templates/manual_override_template.json`
- `templates/bank_manual_override_template.json`
- `templates/reit_manual_override_template.json`

Overrides preserve explicit lineage as `manual_override`. Do not use overrides to
invent values; use them only when an internal/curated source exists.

### C. Real universe / averages workflow

Validate universe coverage:

```bash
python -m sws_engine.cli validate-universe \
  --universe data/universe/universe_US_template.csv \
  --output out/universe_US_coverage.json
```

Build averages:

```bash
python -m sws_engine.cli build-averages \
  --universe data/universe/universe_US_template.csv \
  --market US \
  --date YYYY-MM-DD \
  --min-universe 10 \
  --out-dir data/averages
```

The averages builder supports country -> region -> global -> market fallback and
excludes ETFs/funds/DRs/secondary listings. PB averages use tangible book value
only; rows without explicit intangible assets are excluded from PB aggregation.

### D. Rates / FX sources

Inspect current source files:

```bash
python -m sws_engine.cli rates-report \
  --bond-csv data/rates/bond_yields_10y.csv \
  --erp-json data/rates/erp.json \
  --fx-csv data/fx/fx_eod.csv
```

Real source templates are included:

- `data/rates/bond_yields_10y_real_template.csv`
- `data/rates/erp_real_template.json`
- `data/fx/fx_eod_real_template.csv`

### E. EOD refresh orchestration

Run the operational refresh:

```bash
python -m sws_engine.cli eod-refresh \
  --watchlist data/watchlists/watchlist_synthetic.csv \
  --date YYYY-MM-DD \
  --db data/sws.db \
  --universe data/universe/universe_US-SYN.csv \
  --market US-SYN \
  --logs-dir logs
```

Or use:

```bash
./ops/eod_refresh_real.sh YYYY-MM-DD
```

The EOD runner writes `logs/eod_refresh_<date>.json`, isolates ticker failures
and emits an alert if more than 20% of tickers fail. Live yfinance snapshot
refresh is optional and remains `yfinance_pragmatic` with visible degradation.

Current verification after Step B/C/D/E:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
# 106 passed, 1 skipped
```

## Release Governance, Deployment and E2E — Step F/G/H

This release adds CI/release governance, deployment scaffolding and optional browser E2E validation. It does not change model formulas, the output schema or provider-degradation policy.

### F. CI and release governance

GitHub Actions workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

CI gates:

```bash
ruff check src dashboard tests scripts
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/ci/validate_demo_outputs.py
python scripts/ci/check_no_score_normalized.py
python scripts/ci/check_attribution_footer.py
```

Release gate:

```bash
python -m pytest -q tests/gold tests/portfolio tests/contract
python scripts/ci/validate_demo_outputs.py
python scripts/ci/check_no_score_normalized.py
python scripts/ci/check_attribution_footer.py
python scripts/ci/clean_artifacts.py
```

The governance gates enforce the v3.1 interpretation rules: raw PASS/6 plus coverage, no runtime normalized score, dashboard attribution, and schema-valid demo output.

### G. Deployment and operations

Container scaffolding:

- `Dockerfile` — API/engine container
- `dashboard.Dockerfile` — Streamlit dashboard container
- `docker-compose.yml` — API, dashboard and optional EOD refresh job
- `.env.example` — local configuration template
- `deploy/README.md` and `deploy/production_checklist.md`

Run locally:

```bash
cp .env.example .env
docker compose up --build api dashboard
```

Open:

```text
API:       http://127.0.0.1:8000/docs
Dashboard: http://127.0.0.1:8501
```

Operational scripts:

```bash
BACKUP_DIR=backups ./ops/backup.sh
API_URL=http://127.0.0.1:8000 ./ops/monitoring.sh
```

Security baseline:

```bash
export SWS_API_AUTH_ENABLED=true
export SWS_API_KEY='<long-random-secret>'
export DASHBOARD_API_KEY="$SWS_API_KEY"
```

Do not expose the dashboard publicly without legal/security/model-risk review.

### H. Optional browser E2E

Smoke/component dashboard tests remain part of normal offline CI. Browser E2E is opt-in:

```bash
python -m pip install -e ".[dev,api,dashboard,e2e]"
python -m playwright install chromium
SWS_RUN_E2E_TESTS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -m e2e -q
```

The E2E test starts FastAPI and Streamlit locally, opens the dashboard and checks that the main page renders with the persistent disclaimer.

### Verification after Step F/G/H

```bash
python -m pip install -e ".[dev,api,dashboard,live,ci]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Validation report:

- `validation/validation_report_v3.1_FGH_release_deploy_e2e.md`

Remaining limitations:

- Real data files/universes must still be populated and governed for daily operations.
- Docker images must be built/tested in the target environment.
- E2E and live tests are opt-in.
- External/commercial deployment still requires legal/security review.

## Final Remaining Controls — real-source population and legal scope

This release now includes the final control layer for moving from synthetic/no-network construction data to an internal daily run with real or curated inputs.

### Legal/use-scope gate

Default scope is internal, non-commercial prototype use:

```bash
python -m sws_engine.cli legal-scope-report --scope config/legal_scope.yaml
```

External or commercial access is blocked unless `legal_review_completed=true` is explicitly recorded in `config/legal_scope.yaml`. This gate is operational control, not legal advice.

### Production source registry

The production source registry lists required live/curated sources and marks template/synthetic inputs as not production-ready:

```bash
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness --scope config/legal_scope.yaml --registry config/source_registry.yaml
```

Use `--require-production` to enforce stricter production-real-data requirements:

```bash
python -m sws_engine.cli production-readiness --require-production
```

### Populate real-source working folders

With the `live` extra installed and network access available, populate yfinance snapshots and payloads:

```bash
python -m sws_engine.cli populate-real-sources \
  --watchlist data/watchlists/watchlist_real_template.csv \
  --out-dir data/real_sources \
  --valuation-date 2026-07-08 \
  --refresh
```

The command writes:

- `data/real_sources/snapshots/`
- `data/real_sources/payloads/`
- `data/real_sources/manifests/`

### Curated sources still required from the operator

The package does not bundle proprietary or paid datasets. For a real daily run, the operator must supply versioned curated files:

- curated market universes, for example `data/real_sources/universe/universe_US_curated.csv`;
- 10Y government bond series / 5Y average source files;
- country ERP table;
- EOD FX rates where required;
- manual overrides for analyst estimates, FCF estimates, REIT AFFO/FFO/NAV, and bank NPL/deposits/charge-offs where yfinance is missing.

See `docs/real_data_population_runbook.md`.

## Real Source Population — operator checklist

The current repository is technically complete, but a real daily run still requires operator-supplied, versioned source files. The readiness gate must remain `NOT_READY` until these files are populated with genuine source data and no sample/template/synthetic markers remain.

Detailed checklist:

```text
docs/real_source_population_checklist.md
examples/real_sources/README.md
```

### 1. Populate the market universe

Target path:

```text
data/real_sources/universe/universe_US_curated.csv
```

Start from the shape described in:

```text
examples/real_sources/sample_universe_US.csv
```

Do not copy the sample unchanged. Replace all rows with real listed instruments, record `source`, `source_as_of`, `curated_by`, and `curated_at`, and remove all `sample_only`, `template`, and `synthetic` markers.

Validate:

```bash
python -m sws_engine.cli validate-universe \
  --universe data/real_sources/universe/universe_US_curated.csv \
  --output out/universe_US_coverage.json
```

### 2. Populate 10Y bond yields

Target path:

```text
data/real_sources/rates/bond_yields_10y_curated.csv
```

Use an official or documented curated export. Keep source and date metadata in the file.

### 3. Populate ERP

Target path:

```text
data/real_sources/rates/erp_curated.json
```

ERP is a curated assumption table. Record source, source date, unit, curator and curation timestamp. Do not label illustrative ERP values as curated real data.

### 4. Populate FX EOD when required

Target path:

```text
data/real_sources/fx/fx_eod_curated.csv
```

Required for multi-currency portfolios or FX attribution.

### 5. Run readiness gates

```bash
python -m sws_engine.cli source-registry-report --registry config/source_registry.yaml
python -m sws_engine.cli production-readiness \
  --scope config/legal_scope.yaml \
  --registry config/source_registry.yaml \
  --require-production
```

Supplementary guard:

```bash
python scripts/ci/check_real_source_population_workflow.py
```

This guard writes an evidence report to:

```text
validation/audit_final_artifacts/real_source_population_workflow_report.json
```

Expected status before curated files are populated:

```text
NOT_READY
```

Correct status wording until curated source files and legal scope are cleared:

```text
technical product complete; production use requires curated real-source population and legal scope clearance
```

## CI / deployment final validation

This repository includes the final CI/deployment scaffold. It does not make synthetic or sample data production-ready. Normal CI remains offline; live provider and browser E2E tests are opt-in.

### Local validation commands

```bash
python -m pip install -e ".[dev,api,dashboard,live,ci,e2e]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python scripts/ci/validate_demo_outputs.py
python scripts/ci/check_no_score_normalized.py
python scripts/ci/check_attribution_footer.py
python scripts/ci/check_real_source_population_workflow.py
```

### API and dashboard smoke

```bash
uvicorn sws_engine.api.app:app --host 127.0.0.1 --port 8000
streamlit run dashboard/app.py
```

### Docker compose

```bash
cp .env.example .env
docker compose up --build api dashboard
```

### Ops

```bash
BACKUP_DIR=backups ./ops/backup.sh
API_URL=http://127.0.0.1:8000 ./ops/monitoring.sh
```

`ops/monitoring.py` writes JSON evidence into `logs/` and emits an alert when batch or live snapshot failures exceed 20%.

### Optional tests

```bash
SWS_RUN_LIVE_TESTS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -m live -q
SWS_RUN_E2E_TESTS=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -m e2e -q
```

### Scope limits

- Not investment advice.
- Not the current/live Simply Wall St platform.
- `yfinance_pragmatic` is degraded by design; missing data remains `UNKNOWN`.
- Production use requires curated real-source population and legal scope clearance.
## Real-data dashboard bootstrap

Bring the internal dashboard to a usable state with real `yfinance_pragmatic`
data in three commands:

```bash
cd ~/stock_analysis_gas
source .venv/bin/activate

PYTHONPATH=src python -m sws_engine.cli real-dashboard-bootstrap \
  --tickers AAPL,MSFT,NVDA,GOOGL,AMZN,META,JPM,JNJ,PG,XOM \
  --market US \
  --valuation-date auto \
  --db data/sws.db \
  --refresh \
  --persist

PYTHONPATH=src uvicorn sws_engine.api.app:app --host 127.0.0.1 --port 8000

DASHBOARD_API_URL=http://127.0.0.1:8000 streamlit run dashboard/app.py
```

Optional — create a pragmatic curated universe first:

```bash
PYTHONPATH=src python -m sws_engine.cli create-curated-universe-from-yfinance \
  --tickers AAPL,MSFT,NVDA,GOOGL,AMZN,META,JPM,JNJ,PG,XOM \
  --market US \
  --output data/real_sources/universe/universe_US_curated.csv \
  --refresh
```

What this mode is and is not:

- It uses the live `yfinance_pragmatic` provider. yfinance is not a faithful
  SWS-style data source; degradation is expected and visible.
- Missing data stays `UNKNOWN` — analyst estimates, forward FCF, AFFO/FFO/NAV
  and bank-specific fields are never invented.
- Missing curated rates/ERP produce `MISSING_CURATED_RATE_SOURCE` /
  `MISSING_CURATED_ERP_SOURCE` warnings; dependent checks may be UNKNOWN; the
  bootstrap never crashes because of them.
- `production-readiness` may remain `NOT_READY` until curated universe/rates/
  ERP sources are populated and reviewed. A usable internal dashboard and a
  production-ready source registry are different milestones.
- Internal/non-commercial use only. Not investment advice. Not the live
  Simply Wall St model.

Bootstrap artifacts: `out/real_dashboard_bootstrap/bootstrap_summary.json`,
`out/real_dashboard_bootstrap/bootstrap_report.md`, plus per-ticker
payload/output/report files. New API endpoints: `GET /meta/runtime-summary`,
`GET /companies`. See `docs/real_dashboard_bootstrap_runbook.md`.

