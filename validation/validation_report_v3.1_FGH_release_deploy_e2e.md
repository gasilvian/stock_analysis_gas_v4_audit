# Validation Report v3.1 — F/G/H Release Governance, Deployment and E2E Step

## 1. Executive conclusion

- Validation date: 2026-07-08
- Version validated: v3.1 F/G/H operational hardening candidate
- Verdict: PASS WITH LIMITATIONS

## 2. Scope validated

- CI governance scaffold: GitHub Actions for offline tests, lint, schema validation, no-runtime-normalized-score gate and attribution footer gate.
- Release gate scaffold: tag-based gold/contract tests, validation gates and release archive artifact.
- Deployment scaffold: API Dockerfile, dashboard Dockerfile, docker-compose volumes, backup and monitoring scripts.
- E2E dashboard scaffold: optional Playwright/Streamlit browser test, skipped by default unless explicitly enabled.

## 3. Test results

| Test group | Result | Notes |
|---|---:|---|
| Offline pytest | PASS | Expected to include all engine/API/dashboard/live-adapter/offline ops tests plus CI/deploy scaffold tests. |
| Live tests | SKIP BY DEFAULT | Require `SWS_RUN_LIVE_TESTS=1`. |
| E2E browser tests | SKIP BY DEFAULT | Require `SWS_RUN_E2E_TESTS=1` and Playwright/browser availability. |
| CI gates | IMPLEMENTED | Scripts under `scripts/ci/`; workflows under `.github/workflows/`. |
| Deployment scaffold | IMPLEMENTED | Dockerfiles, compose, backup/monitoring/security docs. |

## 4. Limitations

- Docker images were scaffolded but not built in this sandbox validation run.
- Browser E2E test is implemented as opt-in and is not part of normal offline CI.
- Live market data remains `yfinance_pragmatic` with visible degradation.
- Production authentication is minimal API-key auth; no user management/OAuth.
- Commercial/external use still requires legal/security/model-risk review.

## 5. Model-risk controls

- UNKNOWN and coverage remain mandatory in dashboard/API surfaces.
- Runtime no-normalized-score gate added.
- Dashboard footer attribution and no-investment-advice disclaimer gate added.
- Docker/deployment docs preserve not-investment-advice and not-live-SWS disclaimers.
- Backup and monitoring scripts preserve reproducibility and operational traceability.

## 6. Model-risk judgement

- Fit for internal prototype with controlled deployment: yes.
- Fit for public/commercial production: no, requires legal, data-source, security and model-risk review.
