# Real Dashboard Bootstrap Runbook

Purpose: bring the internal dashboard from "technical product complete" to
"usable with real yfinance_pragmatic data", without inventing missing data and
without touching model logic.

Two distinct end states — do not confuse them:

- **Usable real-data dashboard**: real tickers persisted in SQLite via the
  `yfinance_pragmatic` provider, visible in Company View and Screener, with
  UNKNOWN / warnings / lineage / degradations fully visible. This runbook gets
  you here.
- **Production-ready curated source registry**: curated universe/rates/ERP/FX
  files reviewed by an operator and registered, plus legal scope cleared.
  `production-readiness` may legitimately remain `NOT_READY` while the
  dashboard is already usable. That is expected, not a bug.

## 1. Create a pragmatic real universe from yfinance

```bash
cd ~/stock_analysis_gas
source .venv/bin/activate

PYTHONPATH=src python -m sws_engine.cli create-curated-universe-from-yfinance \
  --tickers AAPL,MSFT,NVDA,GOOGL,AMZN,META,JPM,JNJ,PG,XOM \
  --market US \
  --output data/real_sources/universe/universe_US_curated.csv \
  --refresh
```

Rules baked in:
- `source = yfinance_live_pragmatic_curated`;
- `notes = operator-reviewed yfinance metadata required before production readiness`;
- missing sector/industry/etc. become `UNKNOWN` with a warning in
  `out/real_dashboard_bootstrap/universe_creation_report.md` — never invented;
- Financial Services / Real Estate tickers get `company_type=UNKNOWN` because
  bank/insurance/REIT routing must be operator-confirmed.

If the source registry still requires manual review, `production-readiness`
stays `NOT_READY`. That is acceptable at this stage.

## 2. Run the bootstrap on 10 tickers

```bash
PYTHONPATH=src python -m sws_engine.cli real-dashboard-bootstrap \
  --tickers AAPL,MSFT,NVDA,GOOGL,AMZN,META,JPM,JNJ,PG,XOM \
  --market US \
  --valuation-date auto \
  --db data/sws.db \
  --refresh \
  --persist
```

Per ticker: yfinance live payload → company analysis → schema validation →
SQLite persist → payload/output/report saved under
`out/real_dashboard_bootstrap/`. A failed ticker never stops the batch.
Outputs:
- `out/real_dashboard_bootstrap/bootstrap_summary.json`
- `out/real_dashboard_bootstrap/bootstrap_report.md`

## 3. Start the API

```bash
PYTHONPATH=src uvicorn sws_engine.api.app:app --host 127.0.0.1 --port 8000
```

New read-only endpoints:
- `GET /meta/runtime-summary` — db_path, company_runs_count, latest_run_at,
  tickers_available, production_readiness_hint;
- `GET /companies` — persisted tickers with latest_valuation_date,
  provider_profile, coverage_summary, unknown_checks_count, warnings_count.

## 4. Start the dashboard

```bash
DASHBOARD_API_URL=http://127.0.0.1:8000 streamlit run dashboard/app.py
```

After bootstrap: Company View loads AAPL/MSFT/... from DB; Screener shows real
tickers with `score_raw` + `coverage_pct`; Run & Data Health shows persisted
run count and readiness hint. The dashboard talks to the API only, never to
the DB directly.

## 5. How to interpret UNKNOWN

UNKNOWN means "not evaluable with the available inputs", not a hidden FAIL and
not a neutral PASS. yfinance commonly lacks: analyst estimates with analyst
counts, forward FCF estimates, AFFO/FFO/NAV for REITs, bank NPL/deposit/
charge-off fields, and SWS-style market/industry averages. All of these stay
UNKNOWN with degraded `source_quality` and visible warnings. `score_raw` is
never normalized over known checks.

## 6. Missing curated rates/ERP

The bootstrap never invents bond yields or ERP:
- missing `data/real_sources/rates/bond_yields_10y_curated.csv` →
  warning `MISSING_CURATED_RATE_SOURCE`, discount-rate dependent checks may be
  UNKNOWN, bootstrap continues;
- missing `data/real_sources/rates/erp_curated.json` →
  warning `MISSING_CURATED_ERP_SOURCE`, dependent checks may be UNKNOWN,
  bootstrap continues.

## 7. Path to production-readiness PASS

1. Operator reviews `universe_US_curated.csv` (especially `company_type` and
   any UNKNOWN metadata) and records the review per the source registry.
2. Populate `data/real_sources/rates/bond_yields_10y_curated.csv` and
   `data/real_sources/rates/erp_curated.json` from versioned curated sources.
3. Populate FX curated sources where required.
4. Run `PYTHONPATH=src python -m sws_engine.cli production-readiness` and act
   on remaining findings.
5. Legal scope stays `internal_personal_educational`, non-commercial, no
   external access, unless legal review is completed and recorded.

---

Internal, non-commercial, educational use only. This is not investment advice
and not the live Simply Wall St model. Methodology attribution: Simply Wall St
public Company-Analysis-Model / Portfolio-Analysis-Model repositories
(CC BY-NC-SA 4.0).
