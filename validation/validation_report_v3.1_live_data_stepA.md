# Validation Report v3.1 — Live Data Step A

## 1. Executive conclusion

- Validation date: 2026-07-08
- Version validated: v3.1 Step A live market data adapter
- Verdict: PASS WITH LIMITATIONS

## 2. Scope validated

- yfinance live provider adapter: implemented as `yfinance_pragmatic`
- yfinance mapper: implemented
- Recorded yfinance-shaped fixtures: implemented for offline tests
- CLI live commands: implemented
- FastAPI live endpoints: implemented
- Dashboard live control: implemented in Company View
- Output schema: preserved

## 3. Test results

- Offline test command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q`
- Result: 99 passed, 1 skipped
- Live tests: optional, skipped unless `SWS_RUN_LIVE_TESTS=1`

## 4. yfinance limitations

Fields commonly requiring manual override or curated tables:

- analyst estimates with analyst count per forecast year
- forward FCF estimates
- AFFO/FFO/NAV for REITs
- bank NPL/deposits/charge-offs
- SWS-style market and industry averages
- 10Y government bond 5Y average
- country equity risk premium

## 5. Model-risk controls

- Provider degradation is visible through warnings.
- Missing data is not invented.
- `UNKNOWN` remains visible.
- PB tangible-book rule is preserved; generic book value is not used as exact PB.
- Dividend history is not padded artificially.
- No score normalization was introduced.
- The adapter does not depend on or use the live Simply Wall St model.

## 6. Limitations

- This is not production market-data validation.
- yfinance API shape can change.
- Recorded fixtures are offline yfinance-shaped fixtures; they may be synthetic and are not represented as live fetches.
- Live network tests are opt-in and not part of normal CI.
- Commercial/external use still requires legal/model-risk review.
- Not investment advice.
