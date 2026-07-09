# Specificatie Tehnica v3.1 - SWS Snowflake Engine + Portfolio Model Pack

**Version:** v3.1  
**Date:** 2026-07-06  
**Status:** model pack for controlled implementation  
**Scope:** public GitHub Simply Wall St methodology, documented around 2017-2019.  
**Not in scope:** current/live proprietary Simply Wall St production model.

## 0. Evidence classes

Every material rule must carry a source class:

| Class | Meaning | Implementation rule |
|---|---|---|
| E0 | Explicit rule documented in public GitHub source | Can be implemented as default rule. |
| E1 | Numeric inference validated from a public gold example | Can be implemented if marked as calibrated/inferred and configurable where material. |
| E2 | Own assumption/configurable policy | Must appear in `config/assumptions.yaml`. |
| E3 | Pragmatic implementation decision | Must appear in `docs/implementation_decisions.md`. |
| E4 | Unsupported or insufficiently supported claim | Remove, rewrite or mark out of scope. |

## 1. Model boundaries and disclaimers

This engine implements the public GitHub documentation of Simply Wall St's historical Company Analysis Model and Portfolio Analysis Model. It does not attempt to reproduce the current Simply Wall St live platform.

This output is quantitative exploratory analysis only. It is not investment advice. Any production, commercial or public distribution requires legal and model-risk review, especially because the source methodology is documented as CC BY-NC-SA 4.0.

## 2. Architecture and output contract

### 2.1 Snowflake axes

- 5 axes: Value, Future, Past, Health, Dividend.
- 6 binary checks per axis, total 30 checks.
- Management exists as optional module but does not enter Snowflake score.
- Check results: `PASS`, `FAIL`, `UNKNOWN`.
- Dividend checks #3 and #4 fail by default when the 10-year dividend history is insufficient, according to documented rule.

### 2.2 UNKNOWN scoring policy

For each axis:

```text
score_raw = number of PASS checks, range 0-6
known_checks_count = PASS + FAIL
unknown_checks_count = UNKNOWN
coverage_pct = known_checks_count / 6
score_display = score_raw / 6, without implicit normalization
```

If `score_normalized = PASS / known_checks_count` is ever introduced, it must be displayed separately, marked experimental and never used as the primary Snowflake score.

### 2.3 Company-analysis output schema

```json
{
  "ticker": "AAPL",
  "exchange": "NasdaqGS",
  "valuation_date": "YYYY-MM-DD",
  "provider_profile": "sws_public_faithful_manual_inputs | yfinance_pragmatic",
  "valuation_model": "two_stage_fcf | ddm | excess_returns | affo_dcf",
  "valuation_variant": "base | ffo_fallback | nav_fallback | manual_input | unknown",
  "valuation_model_source_class": "E0 | E1 | E2 | E3 | E4",
  "fair_value": 0.0,
  "price": 0.0,
  "discount_pct": 0.0,
  "scores": {
    "value": {"score_raw": 0, "known_checks_count": 0, "unknown_checks_count": 0, "coverage_pct": 0.0},
    "future": {"score_raw": 0, "known_checks_count": 0, "unknown_checks_count": 0, "coverage_pct": 0.0},
    "past": {"score_raw": 0, "known_checks_count": 0, "unknown_checks_count": 0, "coverage_pct": 0.0},
    "health": {"score_raw": 0, "known_checks_count": 0, "unknown_checks_count": 0, "coverage_pct": 0.0},
    "dividend": {"score_raw": 0, "known_checks_count": 0, "unknown_checks_count": 0, "coverage_pct": 0.0}
  },
  "checks": [
    {
      "axis": "value",
      "id": 1,
      "name": "trading_below_fair_value_20pct",
      "result": "PASS | FAIL | UNKNOWN",
      "reason_code": "OK | MISSING_INPUT | NEGATIVE_DENOMINATOR | PROVIDER_LIMITATION | ASSUMPTION_USED | FAIL_BY_DEFAULT | NOT_APPLICABLE",
      "source_quality": "exact | approximation | assumption | missing",
      "source_class": "E0 | E1 | E2 | E3 | E4",
      "inputs": {},
      "threshold": "",
      "input_lineage": {}
    }
  ],
  "lineage": {
    "price_as_of": "YYYY-MM-DD",
    "financials_as_of": "YYYY-MM-DD",
    "analyst_estimates_as_of": "YYYY-MM-DD",
    "fx_as_of": "YYYY-MM-DD",
    "industry_averages_as_of": "YYYY-MM-DD",
    "assumptions_as_of": "YYYY-MM-DD",
    "provider_versions": {}
  },
  "warnings": []
}
```

## 3. Provider profiles and data quality

### 3.1 `sws_public_faithful_manual_inputs`

This profile is used when inputs required by the public SWS methodology are manually supplied or sourced from curated datasets: analyst estimates with number of analysts per year, FCF estimates, AFFO/FFO/NAV, bank NPL/deposits/charge-offs, industry averages, ERP, CPI/savings rate and 10Y bond 5Y average.

### 3.2 `yfinance_pragmatic`

This profile uses yfinance where available. It cannot be treated as a faithful SWS replica because SWS relied on richer institutional data sources. Missing or approximate fields must be visible via `source_quality`, `reason_code` and `warnings`.

BVB note: for Yahoo Finance, some BVB tickers use `.RO` suffixes, but price and fundamental coverage must be validated per ticker. This is a provider note, not a model rule.

## 4. Model selection and valuation

### 4.1 DCF model-selection truth table

| Company type | Data available | Valuation model | Valuation variant | Source class |
|---|---|---|---|---|
| Non-financial | N/A | `two_stage_fcf` | `base` | E0 |
| Bank / insurance | sufficient bank/insurance data | `excess_returns` | `base` | E0 |
| Bank / insurance | insufficient data | `ddm` | `base` | E0 |
| REIT | AFFO available | `affo_dcf` | `base` | E0 |
| REIT | AFFO unavailable, FFO usable | `affo_dcf` | `ffo_fallback` | E0/E3 |
| REIT | AFFO/FFO unavailable, NAV usable | `affo_dcf` | `nav_fallback` | E0/E3 |
| Other financial | insufficient financial-specific model data | `ddm` | `base` | E0 |
| Any | no valuation inputs | selected model | `unknown` | E3 |

DDM is not the default route for all dividend-paying companies; it is a fallback for financial/REIT branches where the specialized inputs are unavailable.

### 4.2 Discount rate

```text
Discount rate = Cost of Equity = Risk_Free_Rate + Levered_Beta * Equity_Risk_Premium
```

- Risk-free: 5-year average of 10-year government bond yield.
- ERP: country equity risk premium; default source in implementation is assumption/curated table.
- Bottom-up beta: `beta_L = beta_U_industry * (1 + (1 - tax_rate) * D/E)`, bounded to `[0.8, 2.0]`.
- Financial firms: use average levered beta of comparable firms.

### 4.3 Two-stage FCF model

Stage 1 covers 10 years. Analyst FCF estimates are used when available. Missing years are extrapolated with a growth rate converging toward `g = 10Y government bond 5Y average`.

The decay factor `0.7` is **not** presented as an official published rule. It is implemented as an E1 numeric inference calibrated on the AMZN public example and stored in `assumptions.yaml`.

```text
r_t - g = dcf_decay_factor * (r_(t-1) - g)
Terminal_Value = FCF_10 * (1 + g) / (DR - g)
Fair_Value = (sum PV(FCF_1..FCF_10) + PV(Terminal_Value)) / Shares_Outstanding
Discount% = (Fair_Value - Price) / Fair_Value
```

If no analyst estimates are available:

```text
Adjusted_FCF = Operating_Cash_Flow - average_3y_Capex
```

### 4.4 DDM

```text
Value = Expected_DPS / (Discount_Rate - Perpetual_Growth_Rate)
```

`Perpetual_Growth_Rate` is not explicitly defined in the public documentation. Default implementation uses `10Y government bond 5Y average` as E2 assumption, configurable in `assumptions.yaml`.

### 4.5 Excess Returns for banks/insurance

```text
Excess_Return = (Stable_Future_ROE - Cost_of_Equity) * Stable_Future_BVE
Terminal_Value = Excess_Return / (Cost_of_Equity - Expected_Growth_Rate)
Value_Per_Share = (Current_BVE + PV(Terminal_Value)) / Shares_Outstanding
```

Operational definitions:

- `Current_BVE` = latest reported book value of equity.
- `Stable_Future_ROE` = weighted consensus or historical median fallback.
- `Stable_Future_BVE` = projected/stable future BVE from consensus or fallback.
- `Expected_Growth_Rate` is not explicitly defined in public docs; default = 10Y government bond 5Y average, E2, configurable.

Do not implement this formula as generic current `ROE * BVE`.

### 4.6 Relative valuation

```text
PE = Price / EPS_GAAP_Annual
PEG = PE / Net_Income_Growth_Rate_Percent
PB = Price / Tangible_Book_Value_Per_Share
Tangible_Book_Value = Total_Assets - Intangible_Assets - Total_Liabilities
Tangible_Book_Value_Per_Share = Tangible_Book_Value / Shares_Outstanding
```

If the provider cannot supply or reconstruct tangible book value, PB-related checks must be `UNKNOWN` or `approximation`, not `exact`.

## 5. Snowflake checks

Each check returns:

```text
PASS | FAIL | UNKNOWN
reason_code
source_quality
source_class
input_lineage
```

### 5.1 VALUE checks

| ID | Check | PASS condition | Missing/edge policy | Source class |
|---|---|---|---|---|
| V1 | Moderate undervaluation | `Price <= Fair_Value * 0.80` | UNKNOWN if FV or price missing | E0 |
| V2 | Substantial undervaluation | `Price <= Fair_Value * 0.60` | UNKNOWN if FV or price missing | E0 |
| V3 | PE vs market | `0 < PE < PE_median_profitable_market` | UNKNOWN if PE invalid/missing | E0 |
| V4 | PE vs industry | `0 < PE < PE_median_profitable_industry` | UNKNOWN if PE invalid/missing | E0 |
| V5 | PEG | `0 < PEG < 1` | UNKNOWN if growth <=0 or PE invalid | E0 |
| V6 | PB vs industry | `0 < PB < PB_average_industry` | UNKNOWN/approx if tangible BV missing | E0 |

### 5.2 FUTURE checks

| ID | PASS condition | Missing/edge policy | Source class |
|---|---|---|---|
| F1 | Earnings growth > Savings Rate + CPI OR becomes profitable in 5 years | UNKNOWN if growth unavailable | E0 |
| F2 | Earnings growth > weighted market net income growth | UNKNOWN if market average missing | E0 |
| F3 | Revenue growth > weighted market revenue growth | UNKNOWN if revenue growth missing | E0 |
| F4 | Earnings growth > 20% | UNKNOWN if growth missing | E0 |
| F5 | Revenue growth > 20% | UNKNOWN if growth missing | E0 |
| F6 | Estimated ROE in 3 years > 20% | UNKNOWN if estimated ROE missing | E0 |

### 5.3 PAST checks

| ID | PASS condition | Missing/edge policy | Source class |
|---|---|---|---|
| P1 | 1-year EPS growth > industry average EPS growth | UNKNOWN if EPS/industry missing | E0 |
| P2 | Current EPS > EPS 5 years ago | UNKNOWN if history insufficient | E0 |
| P3 | Current LTM YoY EPS growth > 5-year average annual EPS growth | UNKNOWN if history insufficient | E0/E3 |
| P4 | ROE > 20% | UNKNOWN if equity <=0/missing | E0 |
| P5 | Current ROCE > ROCE 3 years ago | UNKNOWN if denominator invalid/missing | E0 |
| P6 | ROA > industry average ROA | UNKNOWN if industry average missing | E0 |

### 5.4 HEALTH checks - non-financial

| ID | PASS condition | Missing/edge policy | Source class |
|---|---|---|---|
| H1 | ST Assets > ST Liabilities | UNKNOWN if missing | E0 |
| H2 | ST Assets > LT Liabilities | UNKNOWN if missing | E0 |
| H3 | Current D/E <= D/E 5 years ago | UNKNOWN if equity invalid/history missing | E0 |
| H4 | D/E < 40% | UNKNOWN if equity <=0/missing | E0 |
| H5 | OCF > 20% * Total Debt | UNKNOWN if OCF/debt missing | E0 |
| H6 | EBIT > 5 * Net Interest Expense, if company pays interest | If no debt/no interest: E3 default PASS; configurable | E0/E3 |

### 5.5 HEALTH checks - loss-making companies

For companies loss-making currently and on average, checks H5-H6 are replaced by cash-runway checks.

| ID | PASS condition | Source class |
|---|---|---|
| H5_loss | Cash + Short-Term Investments covers stable burn > 1 year | E0/E2 |
| H6_loss | Cash + Short-Term Investments covers increasing burn > 1 year | E0/E2 |

`loss_making_average_window_years` defaults to 3 as E2 assumption.

### 5.6 HEALTH checks - financial institutions

| ID | PASS condition | Missing/edge policy | Source class |
|---|---|---|---|
| HF1 | Total Assets < 20 * Equity | UNKNOWN if equity missing/invalid | E0 |
| HF2 | Allowance NPL > 100% * NPL | UNKNOWN if NPL data missing | E0 |
| HF3 | Deposits > 50% * Total Liabilities | UNKNOWN if deposits missing | E0 |
| HF4 | Net Loans < 110% * Total Assets | UNKNOWN if loans/assets missing | E0 |
| HF5 | Loans < 125% * Deposits | UNKNOWN if loans/deposits missing | E0 |
| HF6 | Net Charge-Offs < 3% * Loans | UNKNOWN if charge-offs/loans missing | E0 |

### 5.7 DIVIDEND checks

Dividend_Growth_Rate is an informative metric calculated by linear regression on 10-year DPS history. It does **not** directly determine Dividend checks #3 or #4.

| ID | PASS condition | Missing/edge policy | Source class |
|---|---|---|---|
| D1 | Dividend yield > market P25 | UNKNOWN if yield/percentile missing | E0 |
| D2 | Dividend yield > market P75 | UNKNOWN if yield/percentile missing | E0 |
| D3 | No annual DPS decline > 10% in 10 years | FAIL by default if <10 years history | E0 |
| D4 | Current annualized DPS > annualized DPS 10 years ago | FAIL by default if <10 years history | E0 |
| D5 | 0% < payout < 90%; REIT threshold 100% | UNKNOWN if EPS/DPS invalid | E0 |
| D6 | 0% < estimated payout +3 years < 90%; REIT threshold 100% | UNKNOWN if estimates missing | E0 |

Dividend gate: if yield is in the lower 10th percentile of the market, checks D3-D6 are not evaluated and should return `UNKNOWN` with reason_code `DIVIDEND_GATE_LOW_YIELD`, unless implementing the exact documented behavior requires a different explicit value.

## 6. Growth engine

Priority order:

1. Analyst estimates: weighted linear regression over annual estimates, weighted by analyst count per year, capped at 50 analysts, horizon up to 5 years.
2. Historical: equally weighted regression, minimum 3 years.
3. Fundamentals: ROE convergence to industry median over 5 years; forward earnings use `Earnings_t = ROE_t * Equity_START_t` and `Equity_START_(t+1) = Equity_START_t + Earnings_t * Retention`.

Growth calculation:

```text
Growth = Slope / Mean(abs(values))
```

If earnings are negative at start, annualized growth can be calculated on absolute values for metric display, but checks may fail or become UNKNOWN according to check-specific rules.

## 7. Industry and market averages

Industry and market averages must specify:

- country / region / global fallback level;
- metric type: median profitable, weighted average, percentile, beta aggregate;
- source date;
- provider profile;
- minimum universe count;
- excluded instruments: secondary listings, funds, DRs where relevant.

Implementation default: daily refresh or on-demand for own use. Source-specific refresh claims are not operational requirements.

## 8. Portfolio model

### 8.1 Portfolio types

| Type | Meaning |
|---|---|
| Watchlist | No transactions; synthetic buy per position to back-calculate equal current weights. |
| Holdings | Watchlist + quantity per position; synthetic buy with supplied quantities. |
| Portfolio | Full transaction history. |

ETF/funds are excluded from portfolio Snowflake, except volatility/beta where documented.

### 8.2 Snowflake aggregation

```text
portfolio_axis_score = sum(company_axis_score_raw * current_position_weight)
contributor_value = company_axis_score_raw * current_position_weight
```

Test: sum of contributors per axis equals weighted portfolio axis score.

### 8.3 Returns

Method: money-weighted/dollar-weighted approximation from public model.

```text
Gain = proceeds_from_sales + current_value + dividends_not_reinvested - total_purchased
Total_Return = Gain / Total_Capital_Invested
AYI = weighted average years invested for each buy contribution
CAGR = (1 + Total_Return)^(1 / AYI) - 1
```

The AMZN example implies buy durations are measured to `valuation_date`, including buys that are later sold. This is E1 and must be implemented as configurable behavior.

If `AYI < 1`, do not report annualized CAGR.

### 8.4 FX and corporate actions

- Convert each buy/sell/current value/dividend at EOD FX for the relevant date.
- Separate price gain from FX gain where possible.
- Dividends are included; if reinvested, convert into fractional shares at zero cost on payment date.
- Splits/consolidations are included; fractional outcomes round up according to documented public model behavior.

## 9. Management module

Management is optional and excluded from Snowflake. Flags include CEO compensation relative to size cohort, CEO pay rising while EPS falls, short management tenure, short board tenure and insider net selling.

## 10. Model pack governance

### 10.1 Required files

This specification is part of a model pack containing:

- model card;
- source map;
- claim ledger;
- data contract;
- check engine contract;
- assumptions register;
- output schema;
- test suite;
- validation report template;
- implementation decisions;
- risk register;
- runbook;
- legal notices.

### 10.2 Acceptance gates before coding

- No P0 open.
- All valuation model enums closed.
- Every formula has source reference or test.
- All E2/E3 assumptions registered.
- Every check has PASS/FAIL/UNKNOWN policy.
- Output includes lineage.
- Provider degradations are visible.
- Test suite includes gold tests and synthetic edge cases.

## 11. Minimum test suite

Gold tests:

- AMZN DCF: fair value, terminal value, end-of-year discounting, tolerance ±0.1% FV.
- HemaCare growth: method C, tolerance ±0.1pp.
- FB growth: weighted regression, tolerance ±0.5pp due to rounded public inputs.
- Portfolio AMZN: gain, total return, AYI, CAGR, tolerance ±0.1pp.
- FX example: price gain vs FX gain, exact or ±0.01.

Synthetic tests:

- Dividend history <10 years.
- Dividend drop >10%.
- Current DPS <= DPS 10 years ago.
- EPS negative.
- Equity negative.
- Missing analyst estimates.
- REIT without AFFO/FFO.
- Bank without deposits/NPL.
- Zero debt/no interest expense.
- Missing tangible book value.
- yfinance missing FCF estimates.

## 12. Implementation plan

1. Implement contracts and schemas first.
2. Implement assumption register loader.
3. Implement model-selection truth table.
4. Implement valuation engines.
5. Implement check engine with result contract.
6. Implement lineage and warnings.
7. Implement tests before CLI/reporting.
8. Produce validation report.
9. Only then build UI/report outputs.

## 13. Final status

v3.1 is the controlled implementation baseline. v3 should be treated as superseded for coding because it left unresolved P0 issues in output enum, PB calculation, Excess Returns, Dividend checks and UNKNOWN scoring.
