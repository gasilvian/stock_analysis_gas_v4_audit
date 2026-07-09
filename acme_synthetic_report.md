# Snowflake Report - SYN-ACME (SynEx)

Valuation date: 2026-07-06  
Provider profile: `yfinance_pragmatic`  
Valuation: `two_stage_fcf` / `base` (source class E0)

Fair value: 111.98859487958714 | Price: 92.0 | Discount: 17.8%

## Snowflake scores

| Axis | Score (PASS/6) | Known | Unknown | Coverage |
|---|---|---|---|---|
| value | 3/6 | 6 | 0 | 100% |
| future | 1/6 | 4 | 2 | 67% |
| past | 3/6 | 6 | 0 | 100% |
| health | 5/6 | 6 | 0 | 100% |
| dividend | 4/6 | 5 | 1 | 83% |

## Checks

| Axis | # | Check | Result | Reason | Quality | Class |
|---|---|---|---|---|---|---|
| value | 1 | trading_below_fair_value_20pct | FAIL | OK | missing | E0 |
| value | 2 | trading_below_fair_value_40pct | FAIL | OK | missing | E0 |
| value | 3 | pe_below_market | PASS | OK | approximation | E0 |
| value | 4 | pe_below_industry | PASS | OK | approximation | E0 |
| value | 5 | peg_below_1 | FAIL | OK | approximation | E0 |
| value | 6 | pb_below_industry | PASS | OK | approximation | E0 |
| future | 1 | earnings_growth_above_savings_cpi | UNKNOWN | MISSING_INPUT | missing | E0 |
| future | 2 | earnings_growth_above_market | PASS | OK | approximation | E0 |
| future | 3 | revenue_growth_above_market | FAIL | OK | approximation | E0 |
| future | 4 | earnings_growth_above_20pct | FAIL | OK | approximation | E0 |
| future | 5 | revenue_growth_above_20pct | FAIL | OK | approximation | E0 |
| future | 6 | roe_3y_above_20pct | UNKNOWN | PROVIDER_LIMITATION | missing | E0 |
| past | 1 | eps_growth_1y_above_industry | PASS | OK | approximation | E0 |
| past | 2 | eps_above_5y_ago | PASS | OK | approximation | E0 |
| past | 3 | current_eps_growth_above_5y_average | FAIL | OK | approximation | E0 |
| past | 4 | roe_above_20pct | FAIL | OK | approximation | E0 |
| past | 5 | roce_improved_3y | PASS | OK | approximation | E0 |
| past | 6 | roa_above_industry | FAIL | OK | approximation | E0 |
| health | 1 | st_assets_cover_st_liabilities | PASS | OK | approximation | E0 |
| health | 2 | st_assets_cover_lt_liabilities | FAIL | OK | approximation | E0 |
| health | 3 | debt_to_equity_not_worse_5y | PASS | OK | approximation | E0 |
| health | 4 | debt_to_equity_below_40pct | PASS | OK | approximation | E0 |
| health | 5 | ocf_covers_20pct_debt | PASS | OK | approximation | E0 |
| health | 6 | interest_coverage_above_5x | PASS | OK | approximation | E0 |
| dividend | 1 | yield_above_market_p25 | PASS | OK | approximation | E0 |
| dividend | 2 | yield_above_market_p75 | FAIL | OK | approximation | E0 |
| dividend | 3 | stable_dividend_10y | PASS | OK | approximation | E0 |
| dividend | 4 | dividend_higher_than_10y_ago | PASS | OK | approximation | E0 |
| dividend | 5 | current_payout_sustainable | PASS | OK | approximation | E0 |
| dividend | 6 | future_payout_sustainable | UNKNOWN | PROVIDER_LIMITATION | missing | E0 |

## Warnings

- NOT_INVESTMENT_ADVICE: quantitative exploratory analysis of a public historical methodology; not the live Simply Wall St model
- SYNTHETIC_CURATED_DATA: inputs are synthetic construction data, not real market data
- PROVIDER_LIMITATION: 'fcf_estimates' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'analyst_estimates_weighted' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'earnings_estimates' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'roe_3y_estimate' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'estimated_payout_3y' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'affo_ffo_nav' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'bank_deposits_npl_chargeoffs' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'market_averages' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'industry_averages' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'risk_free_rate_10y_5y_avg' not suppliable by yfinance per SWS definition
- PROVIDER_LIMITATION: 'equity_risk_premium' not suppliable by yfinance per SWS definition
- SYNTHETIC_CURATED_DATA: recorded snapshot contains synthetic values supplied for construction/testing, not real market data
- yfinance_pragmatic outputs are pragmatic approximations, not a faithful replication of the SWS methodology
- FALLBACK: industry 'Utilities' has 3 instruments (< 5); market-level averages used
- SYNTHETIC_CURATED_DATA: industry/market averages built from a synthetic universe for construction/testing
- ASSUMPTION_USED: equity risk premium from curated table (synthetic_curated_construction_table (replace with curated Damodaran-style table before real use))
- PROVIDER_LIMITATION: 'fcf_estimates' not available via yfinance; dependent checks degraded to UNKNOWN
- PROVIDER_LIMITATION: 'analyst_estimates_weighted' not available via yfinance; dependent checks degraded to UNKNOWN
- PROVIDER_LIMITATION: 'roe_3y_estimate' not available via yfinance; dependent checks degraded to UNKNOWN
- PROVIDER_LIMITATION: 'estimated_payout_3y' not available via yfinance; dependent checks degraded to UNKNOWN
- PROVIDER_DEGRADATION: 2 checks UNKNOWN due to provider limitations
- COVERAGE: 3/30 checks UNKNOWN; high scores with low coverage are not comparable to high scores with high coverage
- ADJUSTED_FCF: no analyst FCF estimates; adjusted FCF (OCF - 3y avg capex) with growth route 'historical'

---
*Quantitative exploratory analysis of a public historical methodology. Not investment advice. Not the live Simply Wall St model.*