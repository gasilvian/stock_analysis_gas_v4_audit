"""Map yfinance-shaped raw snapshots into the strict SWS input payload.

This mapper is deliberately conservative: fields not present per the SWS
v3.1 data contract stay missing and degrade to UNKNOWN downstream. It does
not use generic bookValuePerShare as exact PB, does not invent analyst counts,
and does not synthesize AFFO/FFO/NAV or bank NPL/deposit data.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

from sws_engine.core.enums import ProviderProfile, SourceClass, SourceQuality
from sws_engine.providers.provider_lineage import attach_field_lineage, field_meta

PROVIDER = "yfinance"
PROFILE = ProviderProfile.YFINANCE_PRAGMATIC.value

PROVIDER_LIMITATION_WARNINGS = [
    "PROVIDER_LIMITATION: analyst_estimates_weighted not available via yfinance per SWS definition",
    "PROVIDER_LIMITATION: fcf_estimates not available via yfinance; using adjusted FCF fallback if OCF/capex are available",
    "PROVIDER_LIMITATION: AFFO/FFO/NAV not available via yfinance per SWS definition; REIT-specific valuation requires manual override",
    "PROVIDER_LIMITATION: bank NPL/deposits/charge-offs not available via yfinance per SWS definition; financial health checks require manual override",
    "PROVIDER_LIMITATION: market_averages and industry_averages are not available from an individual yfinance ticker; use averages snapshot or manual override",
    "PROVIDER_LIMITATION: risk_free_rate_10y_5y_avg and equity_risk_premium are not available from an equity yfinance ticker; use curated rates/assumptions",
]

ROW_ALIASES = {
    "total_assets": ["Total Assets", "TotalAssets", "totalAssets", "total_assets"],
    "total_liabilities": ["Total Liabilities Net Minority Interest", "Total Liab", "Total Liabilities", "totalLiabilities", "total_liabilities"],
    "st_assets": ["Current Assets", "Total Current Assets", "currentAssets", "st_assets"],
    "st_liabilities": ["Current Liabilities", "Total Current Liabilities", "currentLiabilities", "st_liabilities"],
    "lt_liabilities": ["Long Term Debt And Capital Lease Obligation", "Long Term Liabilities", "longTermLiabilities", "lt_liabilities"],
    "equity": ["Stockholders Equity", "Total Stockholder Equity", "Total Equity Gross Minority Interest", "stockholdersEquity", "equity"],
    "intangible_assets": ["Other Intangible Assets", "Goodwill And Other Intangible Assets", "Intangible Assets", "intangibleAssets", "intangible_assets"],
    "total_debt": ["Total Debt", "totalDebt", "total_debt"],
    "cash_and_st_investments": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "cashAndShortTermInvestments", "cash_and_st_investments"],
    "revenue": ["Total Revenue", "totalRevenue", "revenue"],
    "net_income": ["Net Income", "Net Income Common Stockholders", "netIncome", "net_income"],
    "ebit": ["EBIT", "Ebit", "ebit"],
    "interest_expense": ["Interest Expense", "Interest Expense Non Operating", "interestExpense", "net_interest_expense"],
    "operating_cash_flow": ["Operating Cash Flow", "Total Cash From Operating Activities", "operatingCashFlow", "operating_cash_flow"],
    "capital_expenditure": ["Capital Expenditure", "Capital Expenditures", "capitalExpenditures", "capital_expenditure"],
}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _first(*values: Any) -> Any:
    for v in values:
        if v is not None:
            return v
    return None


def _latest_from_history(raw: dict) -> Tuple[float | None, str | None, str, str]:
    hist = raw.get("history") or []
    # supported shapes: list[{date, close}], dict date->{close}, or dict with Close list.
    if isinstance(hist, list) and hist:
        rows = [r for r in hist if isinstance(r, dict)]
        if rows:
            row = rows[-1]
            value = _num(_first(row.get("close"), row.get("Close"), row.get("regularMarketPrice")))
            as_of = row.get("date") or row.get("Date")
            return value, as_of, "history.close", SourceQuality.EXACT.value
    if isinstance(hist, dict) and hist:
        if "Close" in hist and isinstance(hist["Close"], list) and hist["Close"]:
            dates = hist.get("Date") or hist.get("date") or []
            return _num(hist["Close"][-1]), dates[-1] if dates else None, "history.Close", SourceQuality.EXACT.value
        # date -> close/value dict
        keys = sorted(hist.keys())
        if keys:
            last = hist[keys[-1]]
            if isinstance(last, dict):
                return _num(_first(last.get("close"), last.get("Close"))), keys[-1], "history.close", SourceQuality.EXACT.value
            return _num(last), keys[-1], "history", SourceQuality.EXACT.value
    return None, None, "", SourceQuality.MISSING.value


def _table_latest_value(table: dict | None, aliases: Iterable[str]) -> Tuple[float | None, str | None, str | None]:
    if not isinstance(table, dict):
        return None, None, None
    # simple flat recorded snapshot: {field: value, as_of: date}
    for alias in aliases:
        if alias in table and not isinstance(table[alias], (dict, list)):
            return _num(table[alias]), table.get("as_of") or table.get("date"), alias
    # yfinance-ish table: {row_name: {date: value}}
    for alias in aliases:
        row = table.get(alias)
        if isinstance(row, dict) and row:
            dates = sorted(str(k) for k in row.keys())
            last_date = dates[-1]
            return _num(row[last_date]), last_date, alias
        if isinstance(row, list) and row:
            dates = table.get("columns") or table.get("dates") or []
            return _num(row[0] if len(row) == 1 else row[-1]), (dates[-1] if dates else table.get("as_of")), alias
    return None, None, None


def _table_series(table: dict | None, aliases: Iterable[str]) -> List[float]:
    if not isinstance(table, dict):
        return []
    for alias in aliases:
        row = table.get(alias)
        if isinstance(row, dict) and row:
            return [_num(row[k]) for k in sorted(row.keys()) if _num(row[k]) is not None]
        if isinstance(row, list):
            return [float(v) for v in row if _num(v) is not None]
    return []


def _annual_dividends(raw_divs: Any) -> Tuple[List[float], str | None]:
    if not raw_divs:
        return [], None
    yearly: dict[int, float] = {}
    if isinstance(raw_divs, dict):
        # Already annual: {"2017": 1.0}; or date: amount.
        for k, v in raw_divs.items():
            val = _num(v)
            if val is None:
                continue
            try:
                year = int(str(k)[:4])
            except ValueError:
                continue
            yearly[year] = yearly.get(year, 0.0) + val
    elif isinstance(raw_divs, list):
        for row in raw_divs:
            if not isinstance(row, dict):
                continue
            dt = row.get("date") or row.get("Date")
            val = _num(_first(row.get("dividend"), row.get("Dividends"), row.get("value")))
            if not dt or val is None:
                continue
            try:
                year = int(str(dt)[:4])
            except ValueError:
                continue
            yearly[year] = yearly.get(year, 0.0) + val
    if not yearly:
        return [], None
    years = sorted(yearly.keys())[-10:]
    return [yearly[y] for y in years], str(years[-1])


def _growth_from_series(series: list[float]) -> float | None:
    if len(series) < 2 or series[0] in (0, None):
        return None
    if series[-2] in (0, None):
        return None
    return series[-1] / series[-2] - 1


def _avg_growth(series: list[float]) -> float | None:
    vals = []
    for a, b in zip(series[:-1], series[1:]):
        if a:
            vals.append(b / a - 1)
    return sum(vals) / len(vals) if vals else None


def _put(payload: dict, field: str, value: Any, *, source_field: str, quality: str,
         source_class: str = SourceClass.E3.value, as_of: str | None = None,
         transform: str | None = None) -> None:
    if value is not None:
        payload[field] = value
    attach_field_lineage(payload, field, field_meta(
        provider=PROVIDER, source_field=source_field, source_quality=quality,
        source_class=source_class, as_of=as_of, transform=transform))


def _apply_overrides(payload: dict, overrides: dict | None) -> None:
    if not overrides:
        return
    ov = overrides.get("fields", overrides) if isinstance(overrides, dict) else {}
    for field, spec in ov.items():
        if isinstance(spec, dict) and "value" in spec:
            value = spec.get("value")
            quality = spec.get("source_quality", SourceQuality.EXACT.value)
            source_class = spec.get("source_class", SourceClass.E3.value)
        else:
            value = spec
            quality = SourceQuality.EXACT.value
            source_class = SourceClass.E3.value
        payload[field] = value
        attach_field_lineage(payload, field, field_meta(
            provider="manual_override", source_field=field,
            source_quality=quality, source_class=source_class,
            transform="manual_override"))
    payload.setdefault("builder_warnings", []).append(
        "MANUAL_OVERRIDE_USED: manual override fields applied over yfinance_pragmatic payload")


def map_yfinance_snapshot_to_input_payload(raw_snapshot: dict, valuation_date: str | None = None,
                                           market: str | None = None,
                                           industry: str | None = None,
                                           overrides: dict | None = None) -> dict:
    info = raw_snapshot.get("info") or {}
    fast = raw_snapshot.get("fast_info") or {}
    bs = raw_snapshot.get("balance_sheet") or {}
    inc = raw_snapshot.get("financials") or raw_snapshot.get("income") or {}
    cf = raw_snapshot.get("cashflow") or {}
    raw_divs = raw_snapshot.get("dividends") or raw_snapshot.get("dividends_annual") or {}

    ticker = raw_snapshot.get("ticker") or info.get("symbol") or "UNKNOWN"
    exchange = _first(info.get("exchange"), info.get("fullExchangeName"), market, "UNKNOWN")
    vdate = valuation_date or raw_snapshot.get("valuation_date") or date.today().isoformat()

    payload: dict[str, Any] = {
        "ticker": ticker,
        "exchange": exchange,
        "valuation_date": vdate,
        "provider_profile": PROFILE,
        "company_type": info.get("company_type") or info.get("quoteType") or raw_snapshot.get("company_type") or "non_financial",
        "market": market,
        "industry": industry or info.get("industry"),
        "sector": info.get("sector"),
        "currency": _first(info.get("currency"), fast.get("currency")),
        "financial_currency": _first(info.get("financialCurrency"), info.get("currency"), fast.get("currency")),
        "lineage": {
            "price_as_of": None,
            "financials_as_of": None,
            "analyst_estimates_as_of": None,
            "fx_as_of": None,
            "industry_averages_as_of": None,
            "assumptions_as_of": None,
            "provider_versions": {
                "yfinance": raw_snapshot.get("provider_version", "unknown"),
                "snapshot_kind": raw_snapshot.get("fixture_kind") or raw_snapshot.get("source") or "live_yfinance",
            },
            "field_lineage": {},
        },
        "builder_warnings": [
            "LIVE_YFINANCE_PRAGMATIC: provider coverage may be incomplete; UNKNOWN results reflect missing inputs.",
        ],
    }
    if raw_snapshot.get("fixture_kind"):
        payload["builder_warnings"].append(f"{raw_snapshot['fixture_kind']}: yfinance-shaped recorded fixture used; not a live fetch.")

    # price
    price, price_as_of, source, q = _latest_from_history(raw_snapshot)
    if price is None:
        price = _num(_first(info.get("regularMarketPrice"), info.get("currentPrice"), info.get("previousClose"), fast.get("last_price"), info.get("price")))
        source = "info/fast_info price"
        q = SourceQuality.APPROXIMATION.value if price is not None else SourceQuality.MISSING.value
    payload["lineage"]["price_as_of"] = price_as_of or raw_snapshot.get("fetched_at", "")[:10] or None
    _put(payload, "price", price, source_field=source, quality=q, as_of=payload["lineage"]["price_as_of"])
    if q == SourceQuality.APPROXIMATION.value:
        payload["builder_warnings"].append("PRICE_APPROXIMATION: price did not come from a validated EOD close for valuation_date")

    # identity/share fields
    _put(payload, "shares_outstanding", _num(_first(info.get("sharesOutstanding"), fast.get("shares"), info.get("shares_outstanding"))), source_field="info.sharesOutstanding/fast_info.shares", quality=SourceQuality.APPROXIMATION.value)
    _put(payload, "levered_beta", _num(info.get("beta")), source_field="info.beta", quality=SourceQuality.APPROXIMATION.value)
    _put(payload, "dividend_yield", _num(_first(info.get("dividendYield"), info.get("trailingAnnualDividendYield"))), source_field="info.dividendYield", quality=SourceQuality.APPROXIMATION.value)

    # statement fields
    fin_as_of = None
    for field in ["total_assets", "total_liabilities", "st_assets", "st_liabilities", "lt_liabilities", "equity", "intangible_assets", "total_debt", "cash_and_st_investments"]:
        val, as_of, src = _table_latest_value(bs, ROW_ALIASES[field])
        fin_as_of = fin_as_of or as_of
        if field == "intangible_assets" and val is None:
            attach_field_lineage(payload, field, field_meta(provider=PROVIDER, source_field="balance_sheet.intangible_assets", source_quality=SourceQuality.MISSING.value, source_class=SourceClass.E3.value, as_of=as_of, reason_code="PROVIDER_LIMITATION"))
            payload["builder_warnings"].append("PROVIDER_LIMITATION: intangible_assets not explicitly reported; tangible PB cannot be exact")
        else:
            _put(payload, field, val, source_field=f"balance_sheet.{src or field}", quality=SourceQuality.APPROXIMATION.value if val is not None else SourceQuality.MISSING.value, as_of=as_of)

    if payload.get("equity") is None and payload.get("total_assets") is not None and payload.get("total_liabilities") is not None:
        payload["equity"] = payload["total_assets"] - payload["total_liabilities"]
        attach_field_lineage(payload, "equity", field_meta(provider=PROVIDER, source_field="balance_sheet.total_assets-total_liabilities", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="calculated_from_assets_minus_liabilities"))

    for field in ["revenue", "net_income", "ebit", "interest_expense"]:
        val, as_of, src = _table_latest_value(inc, ROW_ALIASES[field])
        fin_as_of = fin_as_of or as_of
        target = "net_interest_expense" if field == "interest_expense" else field
        # Interest expense often negative in provider statements; model expects net interest expense as positive cost.
        if target == "net_interest_expense" and val is not None:
            val = abs(val)
        _put(payload, target, val, source_field=f"financials.{src or field}", quality=SourceQuality.APPROXIMATION.value if val is not None else SourceQuality.MISSING.value, as_of=as_of)

    ocf, cf_as_of, ocf_src = _table_latest_value(cf, ROW_ALIASES["operating_cash_flow"])
    fin_as_of = fin_as_of or cf_as_of
    _put(payload, "operating_cash_flow", ocf, source_field=f"cashflow.{ocf_src or 'operating_cash_flow'}", quality=SourceQuality.APPROXIMATION.value if ocf is not None else SourceQuality.MISSING.value, as_of=cf_as_of)
    capex_series = _table_series(cf, ROW_ALIASES["capital_expenditure"])
    if capex_series:
        payload["capex_history_3y"] = [abs(v) for v in capex_series[-3:]]
        attach_field_lineage(payload, "capex_history_3y", field_meta(provider=PROVIDER, source_field="cashflow.capital_expenditure", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=cf_as_of, transform="absolute_outflow_last_3y"))
    else:
        attach_field_lineage(payload, "capex_history_3y", field_meta(provider=PROVIDER, source_field="cashflow.capital_expenditure", source_quality=SourceQuality.MISSING.value, source_class=SourceClass.E3.value, as_of=cf_as_of, reason_code="PROVIDER_LIMITATION"))

    payload["lineage"]["financials_as_of"] = fin_as_of or raw_snapshot.get("fetched_at", "")[:10] or None

    # derived ratios/history.
    shares = _num(payload.get("shares_outstanding"))
    ni = _num(payload.get("net_income"))
    if shares and ni is not None:
        eps = ni / shares
        _put(payload, "eps", eps, source_field="net_income/shares_outstanding", quality=SourceQuality.APPROXIMATION.value, as_of=fin_as_of, transform="calculated_eps")
        payload["current_eps"] = eps
        attach_field_lineage(payload, "current_eps", field_meta(provider=PROVIDER, source_field="net_income/shares_outstanding", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="calculated_eps"))
    elif _num(info.get("trailingEps")) is not None:
        eps = _num(info.get("trailingEps"))
        _put(payload, "eps", eps, source_field="info.trailingEps", quality=SourceQuality.APPROXIMATION.value)
        payload["current_eps"] = eps

    rev_series = _table_series(inc, ROW_ALIASES["revenue"])
    ni_series = _table_series(inc, ROW_ALIASES["net_income"])
    if rev_series:
        g = _growth_from_series(rev_series)
        if g is not None:
            payload["revenue_growth"] = g
            attach_field_lineage(payload, "revenue_growth", field_meta(provider=PROVIDER, source_field="financials.revenue_series", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="latest_yoy_growth"))
    if ni_series:
        eps_series = [v / shares for v in ni_series if shares] if shares else []
        if eps_series:
            payload["eps_history"] = eps_series[-6:]
            payload["eps_growth_1y"] = _growth_from_series(eps_series)
            payload["eps_growth_5y_avg"] = _avg_growth(eps_series[-6:])
            if len(eps_series) >= 6:
                payload["eps_5y_ago"] = eps_series[-6]
        eg = _growth_from_series(ni_series)
        if eg is not None:
            payload["earnings_growth"] = eg
            attach_field_lineage(payload, "earnings_growth", field_meta(provider=PROVIDER, source_field="financials.net_income_series", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="latest_yoy_growth"))

    eq = _num(payload.get("equity"))
    assets = _num(payload.get("total_assets"))
    ebit = _num(payload.get("ebit"))
    total_liabilities = _num(payload.get("total_liabilities"))
    st_liabilities = _num(payload.get("st_liabilities"))
    if ni is not None and eq and eq > 0:
        payload["roe"] = ni / eq
        attach_field_lineage(payload, "roe", field_meta(provider=PROVIDER, source_field="net_income/equity", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="calculated_roe"))
    if ni is not None and assets and assets > 0:
        payload["roa"] = ni / assets
        attach_field_lineage(payload, "roa", field_meta(provider=PROVIDER, source_field="net_income/total_assets", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="calculated_roa"))
    if ebit is not None and assets and total_liabilities is not None and st_liabilities is not None:
        capital_employed = assets - st_liabilities
        if capital_employed > 0:
            payload["roce_current"] = ebit / capital_employed
            attach_field_lineage(payload, "roce_current", field_meta(provider=PROVIDER, source_field="ebit/(assets-current_liabilities)", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=fin_as_of, transform="calculated_roce"))

    dps, div_as_of = _annual_dividends(raw_divs)
    if dps:
        payload["dps_history_10y"] = dps
        attach_field_lineage(payload, "dps_history_10y", field_meta(provider=PROVIDER, source_field="dividends", source_quality=SourceQuality.APPROXIMATION.value, source_class=SourceClass.E3.value, as_of=div_as_of, transform="calendar_year_sum_not_padded"))
        if len(dps) < 10:
            payload["builder_warnings"].append("DIVIDEND_HISTORY_INSUFFICIENT: yfinance dividend history has fewer than 10 complete years; D3/D4 fail by default")
    else:
        attach_field_lineage(payload, "dps_history_10y", field_meta(provider=PROVIDER, source_field="dividends", source_quality=SourceQuality.MISSING.value, source_class=SourceClass.E3.value, reason_code="PROVIDER_LIMITATION"))

    # hard missing / external fields.
    for warning in PROVIDER_LIMITATION_WARNINGS:
        payload["builder_warnings"].append(warning)
    for field in ["analyst_estimates_weighted", "fcf_estimates", "earnings_estimates", "roe_3y_estimate", "estimated_payout_3y", "affo_ffo_nav", "bank_deposits_npl_chargeoffs", "market_averages", "industry_averages", "risk_free_rate_10y_5y_avg", "equity_risk_premium"]:
        attach_field_lineage(payload, field, field_meta(provider=PROVIDER, source_field=field, source_quality=SourceQuality.MISSING.value, source_class=SourceClass.E3.value, reason_code="PROVIDER_LIMITATION"))

    _apply_overrides(payload, overrides)
    payload["builder_warnings"] = list(dict.fromkeys(payload["builder_warnings"]))
    return payload


def capability_summary_from_payload(payload: dict) -> dict:
    lineage = ((payload.get("lineage") or {}).get("field_lineage") or {})
    counts = {"exact": 0, "approximation": 0, "assumption": 0, "missing": 0}
    fields = {"exact": [], "approximation": [], "assumption": [], "missing": []}
    for field, meta in lineage.items():
        q = meta.get("source_quality", "missing")
        if q not in counts:
            q = "missing"
        counts[q] += 1
        fields[q].append(field)
    return {"counts": counts, "fields": fields}
