"""Capability matrix: honest field-by-field mapping of what each provider
can supply relative to data_contract.md (Phase 3.1.1).

This is the single source of truth for source_quality per provider field.
'missing' here means the provider CANNOT supply the field per the SWS
definition; the engine must degrade dependent checks, never approximate
silently (risk_register.md)."""

# quality: exact | approximation | assumption | missing
YFINANCE_CAPABILITY = {
    # identity / price
    "ticker": "exact", "exchange": "exact", "price": "exact",
    "shares_outstanding": "approximation",   # float vs point-in-time filings
    "levered_beta": "approximation",         # provider beta, not bottom-up
    # balance sheet
    "total_assets": "exact", "total_liabilities": "exact",
    "intangible_assets": "approximation",    # only when explicitly reported
    "st_assets": "exact", "st_liabilities": "exact", "lt_liabilities": "exact",
    "equity": "exact", "equity_5y_ago": "approximation",
    "debt_current": "exact", "debt_5y_ago": "approximation",
    "total_debt": "exact", "cash_and_st_investments": "exact",
    # income / cashflow
    "eps": "exact", "current_eps": "exact", "eps_5y_ago": "approximation",
    "eps_history": "approximation", "ebit": "exact",
    "net_interest_expense": "approximation",
    "operating_cash_flow": "exact", "capex_history_3y": "exact",
    # dividends
    "dps_history_10y": "exact", "dividend_yield": "exact",
    "payout_ratio": "approximation",
    # ratios / growth inputs
    "roe": "approximation", "roa": "approximation",
    "roce_current": "approximation", "roce_3y_ago": "approximation",
    "eps_growth_1y": "approximation", "eps_growth_5y_avg": "approximation",
    "earnings_growth": "approximation",      # trailing, not SWS forward
    "revenue_growth": "approximation",
    # NOT suppliable by yfinance per SWS definitions -> hard missing
    "fcf_estimates": "missing",              # no forward FCF w/ analyst counts
    "analyst_estimates_weighted": "missing",
    "earnings_estimates": "missing",
    "roe_3y_estimate": "missing",
    "estimated_payout_3y": "missing",
    "affo_ffo_nav": "missing",               # REIT AFFO/FFO not provided
    "bank_deposits_npl_chargeoffs": "missing",
    "market_averages": "missing",            # SWS-style percentiles absent
    "industry_averages": "missing",
    "risk_free_rate_10y_5y_avg": "missing",  # comes from rates module
    "equity_risk_premium": "missing",        # curated table
}

MANUAL_CAPABILITY_DEFAULT = "exact"


def quality_for_field(provider_profile: str, field: str) -> str:
    if provider_profile == "yfinance_pragmatic":
        return YFINANCE_CAPABILITY.get(field, "approximation")
    return MANUAL_CAPABILITY_DEFAULT


def missing_fields(provider_profile: str) -> list:
    if provider_profile == "yfinance_pragmatic":
        return [f for f, q in YFINANCE_CAPABILITY.items() if q == "missing"]
    return []


# Step A live-data capability matrix. This richer table documents yfinance
# field provenance without changing the legacy YFINANCE_CAPABILITY mapping used
# by earlier CLI/tests.
YFINANCE_LIVE_CAPABILITY = [
    {"contract_field":"ticker","yfinance_source":"Ticker/info","yfinance_attribute":"symbol","source_quality":"exact","source_class":"E3","transform":"identity","known_limitations":"ticker validation depends on provider response","dependent_checks":[],"fallback_policy":"manual ticker"},
    {"contract_field":"exchange","yfinance_source":"info","yfinance_attribute":"exchange/fullExchangeName","source_quality":"approximation","source_class":"E3","transform":"provider mapping","known_limitations":"exchange naming differs from SWS exchange names","dependent_checks":[],"fallback_policy":"manual mapping table"},
    {"contract_field":"price","yfinance_source":"history/fast_info/info","yfinance_attribute":"Close/last_price/regularMarketPrice","source_quality":"exact_or_approximation","source_class":"E3","transform":"prefer EOD close","known_limitations":"intraday values are approximation","dependent_checks":["V1","V2","V3","V4","V5","V6"],"fallback_policy":"last close or manual price"},
    {"contract_field":"shares_outstanding","yfinance_source":"info/fast_info","yfinance_attribute":"sharesOutstanding/shares","source_quality":"approximation","source_class":"E3","transform":"none","known_limitations":"point-in-time may not match filing date","dependent_checks":["V6","valuation"],"fallback_policy":"manual input"},
    {"contract_field":"total_assets","yfinance_source":"balance_sheet","yfinance_attribute":"Total Assets","source_quality":"approximation","source_class":"E3","transform":"latest annual period","known_limitations":"provider row names vary","dependent_checks":["V6","P6","HF1"],"fallback_policy":"manual financial statements"},
    {"contract_field":"total_liabilities","yfinance_source":"balance_sheet","yfinance_attribute":"Total Liabilities","source_quality":"approximation","source_class":"E3","transform":"latest annual period","known_limitations":"provider row names vary","dependent_checks":["V6","HF3"],"fallback_policy":"manual financial statements"},
    {"contract_field":"intangible_assets","yfinance_source":"balance_sheet","yfinance_attribute":"Intangible Assets/Goodwill And Other Intangible Assets","source_quality":"approximation_or_missing","source_class":"E3","transform":"only if explicitly reported","known_limitations":"often absent; never infer from bookValuePerShare","dependent_checks":["V6"],"fallback_policy":"manual override or V6 UNKNOWN"},
    {"contract_field":"operating_cash_flow","yfinance_source":"cashflow","yfinance_attribute":"Operating Cash Flow","source_quality":"approximation","source_class":"E3","transform":"latest annual period","known_limitations":"row names vary","dependent_checks":["H5","valuation fallback"],"fallback_policy":"manual cashflow"},
    {"contract_field":"capex_history_3y","yfinance_source":"cashflow","yfinance_attribute":"Capital Expenditure","source_quality":"approximation","source_class":"E3","transform":"absolute outflow, last 3 periods","known_limitations":"sign convention varies","dependent_checks":["valuation fallback"],"fallback_policy":"manual capex history"},
    {"contract_field":"dps_history_10y","yfinance_source":"dividends","yfinance_attribute":"dividend series","source_quality":"approximation","source_class":"E3","transform":"calendar-year sum; no padding","known_limitations":"short history triggers D3/D4 FAIL_BY_DEFAULT","dependent_checks":["D3","D4"],"fallback_policy":"manual DPS history"},
    {"contract_field":"analyst_estimates_weighted","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E3","transform":"none","known_limitations":"no SWS-style forecast year + analyst count","dependent_checks":["F1","F2","F4","F6"],"fallback_policy":"manual analyst estimates or growth fallback"},
    {"contract_field":"fcf_estimates","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E3","transform":"none","known_limitations":"no forward FCF by year with analyst count","dependent_checks":["valuation"],"fallback_policy":"adjusted FCF if OCF/capex available or manual estimates"},
    {"contract_field":"affo_ffo_nav","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E3","transform":"none","known_limitations":"REIT AFFO/FFO/NAV not reliably provided","dependent_checks":["REIT valuation"],"fallback_policy":"manual override"},
    {"contract_field":"bank_deposits_npl_chargeoffs","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E3","transform":"none","known_limitations":"bank health fields absent","dependent_checks":["HF2","HF3","HF4","HF5","HF6"],"fallback_policy":"manual override"},
    {"contract_field":"market_averages","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E3","transform":"none","known_limitations":"not available from individual ticker","dependent_checks":["V3","F1","F2","F3","D1","D2"],"fallback_policy":"averages builder/curated snapshot"},
    {"contract_field":"industry_averages","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E3","transform":"none","known_limitations":"not available from individual ticker","dependent_checks":["V4","V6","P1","P6"],"fallback_policy":"averages builder/curated snapshot"},
    {"contract_field":"risk_free_rate_10y_5y_avg","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E2","transform":"none","known_limitations":"not part of equity ticker data","dependent_checks":["valuation"],"fallback_policy":"rates CSV/assumptions"},
    {"contract_field":"equity_risk_premium","yfinance_source":"none","yfinance_attribute":"n/a","source_quality":"missing","source_class":"E2","transform":"none","known_limitations":"not part of equity ticker data","dependent_checks":["valuation"],"fallback_policy":"ERP curated table/assumptions"},
]

def live_capability_summary():
    counts = {}
    for row in YFINANCE_LIVE_CAPABILITY:
        q = row["source_quality"]
        counts[q] = counts.get(q, 0) + 1
    return {"rows": YFINANCE_LIVE_CAPABILITY, "counts": counts}
