# Validation Report v3.1 — Real Dashboard Bootstrap

## 1. Executive conclusion

- Validation date: 2026-07-08
- Version validated: v3.1 + real-dashboard-bootstrap operational layer
- Verdict: **PASS WITH LIMITATIONS**

Dashboard can be used internally with real yfinance_pragmatic data and visible
UNKNOWN/degradations. Production readiness still requires curated real-source
population for universe/rates/ERP and legal scope remains internal/
non-commercial.

## 2. What was implemented

Operational components only — zero changes to model logic, checks, valuation/
growth/portfolio formulas, `output_schema.json`, UNKNOWN policy, dashboard
architecture (dashboard → API only) or existing API endpoints.

| Component | File(s) | Status |
|---|---|---|
| `real-dashboard-bootstrap` CLI | `src/sws_engine/ops/real_dashboard_bootstrap.py` + `cli.py` dispatch | PASS |
| `create-curated-universe-from-yfinance` CLI | `src/sws_engine/ops/curated_universe.py` + `cli.py` dispatch | PASS |
| `GET /meta/runtime-summary` | `src/sws_engine/api/routes_ops.py` | PASS |
| `GET /companies` | `src/sws_engine/api/routes_ops.py` | PASS |
| Run & Data Health runtime section | `dashboard/pages/4_Run_Data_Health.py` (additive) | PASS |
| Dashboard API client methods | `dashboard/api_client.py` (additive) | PASS |
| Runbook | `docs/real_dashboard_bootstrap_runbook.md` | PASS |
| Offline tests | `tests/ops/*`, `tests/api/test_runtime_summary.py`, `tests/api/test_companies_list.py`, `tests/docs/test_real_dashboard_runbook_exists.py` | PASS (offline, mocked provider) |
| README section | `README.md` | PASS |

## 3. How to run the bootstrap

```bash
PYTHONPATH=src python -m sws_engine.cli real-dashboard-bootstrap \
  --tickers AAPL,MSFT,NVDA,GOOGL,AMZN,META,JPM,JNJ,PG,XOM \
  --market US --valuation-date auto --db data/sws.db --refresh --persist
PYTHONPATH=src uvicorn sws_engine.api.app:app --host 127.0.0.1 --port 8000
DASHBOARD_API_URL=http://127.0.0.1:8000 streamlit run dashboard/app.py
```

## 4. What remains UNKNOWN

With `provider_profile=yfinance_pragmatic`, checks depending on the following
inputs are expected to remain UNKNOWN (never invented, always visible with
degraded `source_quality` and warnings):

- analyst estimates with forecast-year analyst counts;
- forward FCF estimates;
- AFFO/FFO/NAV for REITs;
- bank NPL / deposits / charge-off fields;
- SWS-style market/industry averages where the curated universe is not
  populated/reviewed;
- discount-rate/ERP dependent checks while curated rates/ERP files are absent
  (`MISSING_CURATED_RATE_SOURCE`, `MISSING_CURATED_ERP_SOURCE`).

## 5. Curated sources still missing for production-readiness PASS

1. `data/real_sources/universe/universe_US_curated.csv` — can now be generated
   pragmatically from yfinance, but requires operator review (notably
   `company_type` for Financial Services / Real Estate and any UNKNOWN
   metadata) before it counts as production-curated.
2. `data/real_sources/rates/bond_yields_10y_curated.csv` — must come from a
   versioned curated source; never auto-populated.
3. `data/real_sources/rates/erp_curated.json` — same rule.
4. Legal scope: remains `internal_personal_educational`,
   `commercial_use_enabled=false`, `external_access_enabled=false`,
   `legal_review_completed=false`. Not changed by this work.

Path to PASS: populate + review the three source files, register the review
per the source registry, re-run `production-readiness`.

## 6. Tests

Offline suite (mocked provider, recorded AAPL fixture, no network):

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Expected: previous 122 passed + new tests (bootstrap success/persist, failure
isolation, missing rates/ERP no-crash, no-fake-values payload equality,
min-success-count FAIL path, watchlist input, runtime-summary, companies list,
curated-universe UNKNOWN handling, runbook existence). 2 live tests remain
skipped by default (`SWS_RUN_LIVE_TESTS=1` opt-in).

Governance gates expected green:

```bash
python scripts/ci/validate_demo_outputs.py
python scripts/ci/check_no_score_normalized.py
python scripts/ci/check_attribution_footer.py
python scripts/ci/check_real_source_population_workflow.py
```

CI expected: green (offline tests + ruff + existing gates; no schema change,
no `score_normalized` anywhere in new code, attribution footer present in all
new reports).

## 7. Limitations

- `yfinance_pragmatic` provider: not a faithful SWS/S&P Capital IQ data
  source; degradation is intrinsic and visible.
- Missing analyst estimates, forward FCF estimates, AFFO/FFO/NAV, and
  bank-specific fields — dependent checks stay UNKNOWN.
- Rates/ERP may be absent unless curated; dependent checks stay UNKNOWN.
- Curated universe generated from yfinance is pragmatic, not reviewed;
  production-readiness may legitimately remain NOT_READY.
- Not investment advice. Non-commercial, internal use only. Not the live
  Simply Wall St model.

## 8. Explicit confirmations

- No financial model logic changed.
- No `output_schema.json` change.
- No fake real data introduced (offline test asserts the persisted payload is
  byte-identical to the mapper output; curated universe writes UNKNOWN for
  missing metadata).
- UNKNOWN / warnings / source_quality / source_class / input_lineage
  preserved end-to-end and surfaced in dashboard/API.
- `score_normalized` is never computed.
- production-readiness is never forced to PASS.

---

Internal, non-commercial, educational use only. Not investment advice. Not
the live Simply Wall St model. Methodology attribution: Simply Wall St public
Company-Analysis-Model / Portfolio-Analysis-Model repositories
(CC BY-NC-SA 4.0).
