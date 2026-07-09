# yfinance Capability Matrix — Step A

This matrix is intentionally conservative. `yfinance_pragmatic` is not a faithful SWS/S&P Capital IQ replacement. Missing fields must remain missing, dependent checks become `UNKNOWN`, and provider limitations are visible in warnings.

| Contract field | yfinance source | Quality | Limitation | Fallback |
|---|---|---|---|---|
| ticker | Ticker/info | exact | Provider validation can fail | manual ticker |
| exchange | info.exchange/fullExchangeName | approximation | Exchange naming differs | mapping/manual |
| price | history Close / fast_info / info | exact or approximation | Intraday/last_price is not EOD | last close/manual |
| shares_outstanding | info.sharesOutstanding / fast_info.shares | approximation | Point-in-time mismatch | manual input |
| total_assets/liabilities/equity | balance_sheet | approximation | Row names vary | manual statements |
| intangible_assets | balance_sheet explicit row only | approximation or missing | Often absent; never infer | manual override or V6 UNKNOWN |
| operating_cash_flow | cashflow | approximation | Row names vary | manual cashflow |
| capex_history_3y | cashflow capital expenditure | approximation | Sign convention varies | manual capex |
| dps_history_10y | dividends | approximation | No padding; short history fails D3/D4 | manual DPS history |
| analyst_estimates_weighted | none | missing | No SWS forecast-year + analyst count | manual estimates |
| fcf_estimates | none | missing | No forward FCF series | adjusted FCF or manual |
| affo_ffo_nav | none | missing | REIT AFFO/FFO/NAV not robust | manual override |
| bank_deposits_npl_chargeoffs | none | missing | Bank-specific health data absent | manual override |
| market_averages/industry_averages | none | missing | Not available from single ticker | averages builder/curated snapshot |
| risk_free_rate_10y_5y_avg / ERP | none | missing | Not equity ticker data | rates tables/assumptions |

Rule: prefer `missing` over false precision.
