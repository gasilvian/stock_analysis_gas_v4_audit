# Validation Report v3.1 — Operational Steps B/C/D/E

## 1. Executive conclusion

- Validation date: 2026-07-08
- Version validated: v3.1 operational B/C/D/E candidate
- Verdict: PASS WITH LIMITATIONS

## 2. Scope validated

- B: manual override workflow and dry-run input validation
- C: real-universe averages builder with country/region/global fallback
- D: versioned rates/FX source inspection
- E: EOD refresh orchestration and logs

## 3. Test results

- Offline pytest suite: 106 passed, 1 skipped (live optional) without network.
- Live provider tests remain optional and skipped unless `SWS_RUN_LIVE_TESTS=1`.

## 4. Limitations

- Real market universes are seeded as templates; production use requires curation.
- Rates/FX real files are templates until populated from FRED/BNR/curated sources.
- EOD refresh can run in recorded/synthetic mode or live yfinance mode, but live yfinance remains pragmatic and degraded.
- No Docker/deployment/monitoring stack yet beyond simple JSON logs and shell runner.
- No commercial/legal clearance.

## 5. Model-risk controls

- Manual overrides preserve lineage and source_quality.
- Missing values remain UNKNOWN unless explicitly overridden.
- Averages PB calculation uses tangible book value only.
- Coverage and provider degradation remain visible.
- No `score_normalized` introduced.

## 6. Model-risk judgement

- Fit for internal controlled prototype: yes.
- Fit for production/commercial deployment: no, requires source curation, CI, Docker, monitoring and legal review.
