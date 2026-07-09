# Validation Report v3.1 — API Step 2 / FastAPI Backend Layer

## 1. Executive conclusion

- **Validation date:** 2026-07-08
- **Validator:** implementation self-check assisted by ChatGPT
- **Version validated:** `sws-snowflake-engine` 3.1.0 + FastAPI API layer `0.1.0`
- **Verdict:** **PASS WITH LIMITATIONS**

The API layer is fit for internal dashboard development over the existing synthetic/no-network release candidate. It is not production-ready, does not include live market-data ingestion, and is not validated for commercial deployment.

## 2. Scope validated

- **FastAPI app:** implemented in `src/sws_engine/api/app.py` with company, portfolio, query, governance and meta routes.
- **Company API:** `POST /analyze/company`, `GET /companies/{ticker}/latest`, `GET /companies/{ticker}/history`, `GET /companies/{ticker}/checks`.
- **Portfolio API:** `POST /analyze/portfolio`, `GET /portfolios/{portfolio_id}/latest`, `GET /portfolios/{portfolio_id}/history`.
- **Query/governance API:** `GET /screener`, `GET /averages/{market}/{date}`, `GET /assumptions/current`.
- **Meta API:** `GET /`, `GET /meta/health`, OpenAPI schema.
- **Security:** optional `X-API-Key` mode with `SWS_API_AUTH_ENABLED` and `SWS_API_KEY`.
- **Persistence:** API writes to and reads from the existing SQLite store without changing the output JSON as source of truth.

## 3. Source traceability and model-contract controls

| Control | Status | Notes |
|---|---:|---|
| Company analysis returns schema-valid engine output | PASS | `POST /analyze/company` test validates output against `schemas/output_schema.json`. |
| Engine output is not remodeled | PASS | API metadata is wrapped separately under `metadata`; full output remains under `output`. |
| Checks, warnings, lineage and provider profile are preserved | PASS | Company API test verifies checks/scores/lineage/warnings. |
| UNKNOWN and provider warnings remain visible | PASS | Degraded yfinance-style payload test verifies warnings and UNKNOWN checks. |
| Coverage is exposed in history and screener | PASS | API query tests verify `coverage_pct` in responses. |
| Screener applies coverage with score | PASS | Default `min_coverage=0.66`; tests check coverage is returned and filtered. |
| API auth can be enabled | PASS | `X-API-Key` positive/negative tests pass. |
| Synthetic/no-network data layer is explicit | PASS | `/meta/health` returns `data_layer=synthetic/no-network` and `live_market_data=false`. |

## 4. Test results

Command executed:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Observed result:

```text
61 passed in 8.35s
```

API test coverage added:

| Test area | Result |
|---|---:|
| Root and OpenAPI schema | PASS |
| Meta health | PASS |
| Company analysis, schema validation and persistence | PASS |
| Latest company output | PASS |
| Company history with score and coverage | PASS |
| Check filtering, including UNKNOWN | PASS |
| Screener with coverage | PASS |
| Portfolio analysis, latest and history | PASS |
| Assumptions hash/current policy endpoint | PASS |
| API key auth | PASS |
| Error handling for invalid input and missing resources | PASS |

## 5. Limitations

- **Synthetic/no-network data layer:** unchanged from the Phase 4 candidate.
- **No live market data:** no `yfinance_live.py`, no real provider mapper, no live rates/FX ingestion.
- **No dashboard:** this step prepares the backend for Streamlit/React but does not implement UI.
- **No Docker/deployment:** operational packaging, backup, monitoring and public exposure are out of scope.
- **No production hardening:** API key auth is minimal and intended for internal use.
- **No commercial/legal clearance:** source methodology remains treated as CC BY-NC-SA 4.0; external/commercial use requires review.
- **Not investment advice:** output remains quantitative exploratory analysis of a public historical methodology and is not the live Simply Wall St model.

## 6. Model-risk judgement

- **Fit for internal backend prototype:** yes.
- **Fit for dashboard development over synthetic/no-network data:** yes.
- **Fit for production:** no.
- **Fit for commercial deployment:** no.

Required remediation before production:

1. Implement live provider ingestion and field-level capability validation.
2. Validate real industry/market averages and rates/FX feeds.
3. Add dashboard with explicit UNKNOWN/coverage visibility.
4. Add Docker/deployment, monitoring and backup.
5. Complete legal and model-risk review for external/commercial use.
