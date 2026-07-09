# Snowflake Report - DEMO (DemoEX)

Valuation date: 2026-07-06  
Provider profile: `sws_public_faithful_manual_inputs`  
Valuation: `two_stage_fcf` / `manual_input` (source class E3)

Fair value: 120.0 | Price: 80.0 | Discount: 33.3%

## Snowflake scores

| Axis | Score (PASS/6) | Known | Unknown | Coverage |
|---|---|---|---|---|
| value | 5/6 | 6 | 0 | 100% |
| future | 5/6 | 6 | 0 | 100% |
| past | 6/6 | 6 | 0 | 100% |
| health | 5/6 | 6 | 0 | 100% |
| dividend | 5/6 | 6 | 0 | 100% |

## Checks

| Axis | # | Check | Result | Reason | Quality | Class |
|---|---|---|---|---|---|---|
| value | 1 | trading_below_fair_value_20pct | PASS | OK | exact | E0 |
| value | 2 | trading_below_fair_value_40pct | FAIL | OK | exact | E0 |
| value | 3 | pe_below_market | PASS | OK | exact | E0 |
| value | 4 | pe_below_industry | PASS | OK | exact | E0 |
| value | 5 | peg_below_1 | PASS | OK | exact | E0 |
| value | 6 | pb_below_industry | PASS | OK | exact | E0 |
| future | 1 | earnings_growth_above_savings_cpi | PASS | OK | exact | E0 |
| future | 2 | earnings_growth_above_market | PASS | OK | exact | E0 |
| future | 3 | revenue_growth_above_market | PASS | OK | exact | E0 |
| future | 4 | earnings_growth_above_20pct | PASS | OK | exact | E0 |
| future | 5 | revenue_growth_above_20pct | FAIL | OK | exact | E0 |
| future | 6 | roe_3y_above_20pct | PASS | OK | exact | E0 |
| past | 1 | eps_growth_1y_above_industry | PASS | OK | exact | E0 |
| past | 2 | eps_above_5y_ago | PASS | OK | exact | E0 |
| past | 3 | current_eps_growth_above_5y_average | PASS | OK | exact | E0 |
| past | 4 | roe_above_20pct | PASS | OK | exact | E0 |
| past | 5 | roce_improved_3y | PASS | OK | exact | E0 |
| past | 6 | roa_above_industry | PASS | OK | exact | E0 |
| health | 1 | st_assets_cover_st_liabilities | PASS | OK | exact | E0 |
| health | 2 | st_assets_cover_lt_liabilities | FAIL | OK | exact | E0 |
| health | 3 | debt_to_equity_not_worse_5y | PASS | OK | exact | E0 |
| health | 4 | debt_to_equity_below_40pct | PASS | OK | exact | E0 |
| health | 5 | ocf_covers_20pct_debt | PASS | OK | exact | E0 |
| health | 6 | interest_coverage_above_5x | PASS | OK | exact | E0 |
| dividend | 1 | yield_above_market_p25 | PASS | OK | exact | E0 |
| dividend | 2 | yield_above_market_p75 | FAIL | OK | exact | E0 |
| dividend | 3 | stable_dividend_10y | PASS | OK | exact | E0 |
| dividend | 4 | dividend_higher_than_10y_ago | PASS | OK | exact | E0 |
| dividend | 5 | current_payout_sustainable | PASS | OK | exact | E0 |
| dividend | 6 | future_payout_sustainable | PASS | OK | exact | E0 |

## Warnings

- NOT_INVESTMENT_ADVICE: quantitative exploratory analysis of a public historical methodology; not the live Simply Wall St model
- DEMO_FIXTURE_ONLY: synthetic input data used for development/testing, not real company analysis

---
*Quantitative exploratory analysis of a public historical methodology. Not investment advice. Not the live Simply Wall St model.*