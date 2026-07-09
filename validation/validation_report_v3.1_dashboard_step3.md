# Validation Report v3.1 — Dashboard Step 3 / Streamlit UI Layer

## 1. Executive conclusion

- **Validation date:** 2026-07-08
- **Validator:** implementation self-check assisted by ChatGPT
- **Version validated:** `sws-snowflake-engine` 3.1.0 + FastAPI API layer `0.1.0` + Streamlit dashboard prototype
- **Verdict:** **PASS WITH LIMITATIONS**

The dashboard layer is fit for internal prototype and governance review over the existing FastAPI backend. It is not production-ready, does not include live market-data ingestion, and is not validated for commercial or public deployment.

## 2. Scope validated

- **Dashboard entry point:** `dashboard/app.py`.
- **API client:** `dashboard/api_client.py`, consuming FastAPI over HTTP only.
- **Company View:** `dashboard/pages/1_Company_View.py` with Snowflake radar, raw scores, coverage, valuation card, checks table, warnings, lineage and history.
- **Portfolio View:** `dashboard/pages/2_Portfolio_View.py` with weighted Snowflake, positions/returns and contributor display when present.
- **Screener:** `dashboard/pages/3_Screener.py` with score and mandatory coverage filtering.
- **Run & Data Health:** `dashboard/pages/4_Run_Data_Health.py` with API/data-layer status.
- **Assumptions & Governance:** `dashboard/pages/5_Assumptions_Governance.py` with assumptions hash, UNKNOWN scoring policy and provider profiles.
- **Reusable components:** badges, footer, radar, score cards, warnings panel, lineage panel, checks table, valuation card and portfolio components.

## 3. Model-risk controls

| Control | Status | Notes |
|---|---:|---|
| Dashboard consumes FastAPI only | PASS | Dashboard code uses `dashboard/api_client.py`; no direct engine or SQLite imports. |
| UNKNOWN visible | PASS | Checks table and warnings panel preserve UNKNOWN and reason codes. |
| Coverage visible | PASS | Radar and screener require/display `coverage_pct`; history refuses score-only display. |
| No normalization | PASS | No `score_normalized` is computed or displayed. |
| yfinance pragmatic banner | PASS | Company View flags `provider_profile=yfinance_pragmatic`. |
| Synthetic/demo warning visible | PASS | DEMO/SYNTHETIC warnings trigger visible banners. |
| source_quality/source_class visible | PASS | Checks table exposes both fields. |
| Warnings visible | PASS | Warnings panel highlights provider limitations, assumptions and synthetic/demo markers. |
| Footer disclaimer and attribution | PASS | Footer component is used by all dashboard pages. |

## 4. Test results

Command executed:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Observed result:

```text
75 passed in 8.81s
```

Dashboard test coverage added:

| Test area | Result |
|---|---:|
| Dashboard module and page imports | PASS |
| No direct engine/SQLite imports in dashboard | PASS |
| API client GET/POST wrappers and API-key header | PASS |
| 404 and API-down handling | PASS |
| Snowflake radar score extraction and coverage requirement | PASS |
| Check result contract validation | PASS |
| Warning classification | PASS |
| Badge classification for provider/result/source states | PASS |

## 5. Limitations

- **Synthetic/no-network data layer:** unchanged from the release candidate.
- **No live market data:** no live yfinance mapper or real provider ingestion in this step.
- **Dashboard is an internal prototype:** no production hardening, no browser E2E tests and no multi-user auth.
- **No Docker/deployment:** operational packaging, backup, monitoring and public exposure are out of scope.
- **No commercial/legal clearance:** source methodology remains treated as CC BY-NC-SA 4.0; external/commercial use requires review.
- **Not investment advice:** output remains quantitative exploratory analysis of a public historical methodology and is not the live Simply Wall St model.

## 6. Model-risk judgement

- **Fit for internal dashboard prototype:** yes.
- **Fit for governance review over synthetic/no-network data:** yes.
- **Fit for production:** no.
- **Fit for commercial deployment:** no.

Required remediation before production:

1. Implement live provider ingestion and field-level capability validation.
2. Validate real industry/market averages and rates/FX feeds.
3. Add browser end-to-end tests and deployment packaging.
4. Add production auth, monitoring, backups and operational runbooks.
5. Complete legal and model-risk review for external/commercial use.
