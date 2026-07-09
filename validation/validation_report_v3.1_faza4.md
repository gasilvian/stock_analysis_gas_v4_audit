# Validation Report v3.1 — Phase 4 Candidate Build

## 1. Executive conclusion

- **Validation date:** 2026-07-08
- **Validator:** implementation self-check assisted by ChatGPT
- **Version validated:** `sws-snowflake-engine` 3.1.0, Phase 4 Candidate Build
- **Verdict:** **PASS WITH LIMITATIONS**

The build is fit for a controlled prototype/demo. It is not production-ready and is not validated for commercial deployment. The current data layer is synthetic/no-network construction data, not live market data.

## 2. Scope validated

- **Company valuation engine:** validated at prototype level through contract, gold, synthetic and integration tests.
- **Check engine:** validated for 30 Snowflake checks and full check-result contract.
- **Portfolio engine:** validated for returns, AYI/CAGR, FX split, corporate actions and weighted Snowflake aggregation.
- **Provider profile:** `sws_public_faithful_manual_inputs` and degradation-aware `yfinance_pragmatic` stub/recorded construction mode.
- **Assumption profile:** `config/assumptions.yaml` loaded and used with E1/E2/E3 policies.
- **Persistence/batch:** SQLite schema, batch execution, history and screener CLI validated at Phase 4 prototype level.

## 3. Source traceability and P0 controls

| Rule / formula / control | Source class | Validated? | Notes |
|---|---:|---:|---|
| Output uses `valuation_model` and `valuation_variant` enums | E0/E3 | Yes | Output validates against `schemas/output_schema.json`. |
| Every Snowflake check returns `PASS` / `FAIL` / `UNKNOWN` plus `reason_code`, `source_quality`, `source_class`, `inputs`, `threshold`, `input_lineage` | E0 | Yes | Contract tests and demo/integration tests pass. |
| UNKNOWN scoring uses raw `PASS/6`, `known_checks_count`, `unknown_checks_count`, `coverage_pct`; no implicit normalization | E3 | Yes | Tested; no primary normalized score used. |
| PB uses tangible book value per share, not generic book value per share | E0 | Yes | Synthetic negative test covers missing tangible book value. |
| Excess Returns uses stable/future ROE and BVE, not generic current ROE/BVE | E0/E2 | Yes | Synthetic bank test covers the branch. |
| Dividend growth regression is not used for D3/D4 scoring | E0 | Yes | D3/D4 direct DPS-history tests pass. |
| D3/D4 fail by default when DPS history is shorter than 10 years | E0 | Yes | Synthetic dividend-history test passes. |
| `yfinance_pragmatic` degradation is visible | E3 | Yes | Warnings and provider-limitation behavior tested. |
| Assumptions are externalized in `config/assumptions.yaml` | E1/E2/E3 | Yes | Loader and policy tests pass. |
| Portfolio buy-duration policy and ACT/365.25 convention | E1/E3 | Yes | Portfolio gold/synthetic tests pass. |

## 4. Test results

Command executed:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Observed result:

```text
44 passed in 7.62s
```

| Test group | Result | Notes |
|---|---:|---|
| Contract tests | PASS | Output schema and check-result contract validated. |
| Gold tests | PASS | AMZN DCF, FB growth, HemaCare growth, portfolio AMZN and FX split. |
| Synthetic edge tests | PASS | Dividend history, dividend drop, missing tangible BV, negative equity, negative EPS, H6 no-debt policy, strict-mode no autofill. |
| Company-type variants | PASS | REIT, bank, loss-making, growth fallback, adjusted FCF and management-exclusion behavior. |
| Portfolio engine | PASS | Holdings/watchlist/portfolio behavior, returns, FX, splits/reinvestment and contributor invariant. |
| CLI/integration | PASS | Company and portfolio CLI paths validate schema and reports. |
| Phase 3 data layer | PASS | Synthetic/no-network payload building, averages, rates/FX and provider degradation behavior. |
| Phase 4 persistence | PASS | SQLite store, batch runner, history and screener query paths. |

## 5. Limitations

- **Synthetic/no-network data layer:** `data/recorded`, `data/universe`, `data/rates` and `data/fx` are construction/demo datasets. They are not live market data.
- **No live yfinance ingestion:** `providers/yfinance_pragmatic.py` is degradation-aware, but a full `yfinance_live.py` mapper is not implemented in this candidate.
- **Industry/market averages:** builder is validated on synthetic universe data. Real market universes, fallback hierarchy and production refresh require separate validation.
- **Rates/FX:** current files are curated/synthetic examples. Real FRED/BNR/Damodaran-style data sources are not wired as production feeds.
- **No FastAPI layer:** API product phase is not implemented.
- **No dashboard:** Streamlit/React dashboard is not implemented.
- **No Docker/deployment package:** production deployment, backup and monitoring are not implemented.
- **No commercial/legal clearance:** source methodology is treated as CC BY-NC-SA 4.0; commercial use needs legal review.
- **Not investment advice:** outputs are quantitative exploratory analysis of a public historical methodology and are not the live Simply Wall St platform.

## 6. Model-risk judgement

- **Fit for controlled prototype:** yes.
- **Fit for demo using synthetic/recorded construction data:** yes.
- **Fit for production:** no.
- **Fit for commercial deployment:** no, pending legal and model-risk review.

Required remediation before production:

1. Implement and validate live provider ingestion.
2. Build real industry/market universes and refresh workflow.
3. Add API layer and dashboard with coverage/UNKNOWN visibility.
4. Add CI release gates and validation snapshots per tagged release.
5. Complete legal review for any external or commercial deployment.
