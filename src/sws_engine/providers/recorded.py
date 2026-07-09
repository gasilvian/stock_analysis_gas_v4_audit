"""Recorded-snapshot provider (Phase 3.1, no-network mode).

Loads a provider snapshot JSON from disk exactly as a live fetcher would
return it, then maps it to the engine payload using the capability matrix.
A future live yfinance fetcher only needs to produce the same snapshot
shape and drop it in data/recorded/ - the mapper and everything downstream
stay unchanged.

Snapshot shape:
{
  "source": "yfinance" | "synthetic_curated",
  "fetched_at": "YYYY-MM-DD",
  "ticker": "...", "exchange": "...", "currency": "...",
  "info": {...}, "balance_sheet": {...}, "income": {...},
  "cashflow": {...}, "dividends_annual": {"2017": 1.0, ...}
}
All snapshots shipped in this phase are SYNTHETIC, provided for correct
construction only, and flagged as such in output warnings."""
import json
import os

from sws_engine.providers.capability_matrix import (
    YFINANCE_CAPABILITY, quality_for_field,
)
from sws_engine.providers.base import BaseProvider, ProviderResult


def load_snapshot(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def map_snapshot_to_payload(snap: dict) -> dict:
    info = snap.get("info", {})
    bs = snap.get("balance_sheet", {})
    inc = snap.get("income", {})
    cf = snap.get("cashflow", {})
    div = snap.get("dividends_annual", {}) or {}

    dps = [div[y] for y in sorted(div.keys())]
    payload = {
        "ticker": snap["ticker"], "exchange": snap.get("exchange"),
        "currency": snap.get("currency"),
        "price": info.get("price"),
        "shares_outstanding": info.get("shares_outstanding"),
        "levered_beta": info.get("levered_beta"),
        "company_type": info.get("company_type", "non_financial"),
        "total_assets": bs.get("total_assets"),
        "intangible_assets": bs.get("intangible_assets"),
        "total_liabilities": bs.get("total_liabilities"),
        "st_assets": bs.get("st_assets"),
        "st_liabilities": bs.get("st_liabilities"),
        "lt_liabilities": bs.get("lt_liabilities"),
        "equity": bs.get("equity"), "equity_5y_ago": bs.get("equity_5y_ago"),
        "debt_current": bs.get("debt_current"),
        "debt_5y_ago": bs.get("debt_5y_ago"),
        "total_debt": bs.get("total_debt"),
        "cash_and_st_investments": bs.get("cash_and_st_investments"),
        "eps": inc.get("eps"), "current_eps": inc.get("eps"),
        "eps_5y_ago": inc.get("eps_5y_ago"),
        "eps_history": inc.get("eps_history"),
        "eps_growth_1y": inc.get("eps_growth_1y"),
        "eps_growth_5y_avg": inc.get("eps_growth_5y_avg"),
        "earnings_growth": inc.get("earnings_growth_trailing"),
        "revenue_growth": inc.get("revenue_growth_trailing"),
        "ebit": inc.get("ebit"),
        "net_interest_expense": inc.get("net_interest_expense"),
        "roe": inc.get("roe"), "roa": inc.get("roa"),
        "roce_current": inc.get("roce_current"),
        "roce_3y_ago": inc.get("roce_3y_ago"),
        "operating_cash_flow": cf.get("operating_cash_flow"),
        "capex_history_3y": cf.get("capex_history_3y"),
        "fcf_history": cf.get("fcf_history"),
        "earnings_history": inc.get("earnings_history"),
        "dps_history_10y": dps if dps else None,
        "dividend_yield": info.get("dividend_yield"),
        "payout_ratio": inc.get("payout_ratio"),
        "lineage": {
            "price_as_of": snap.get("fetched_at"),
            "financials_as_of": bs.get("as_of") or inc.get("as_of"),
            "analyst_estimates_as_of": None,
            "fx_as_of": None, "industry_averages_as_of": None,
            "assumptions_as_of": None,
            "provider_versions": {
                "recorded_snapshot": snap.get("source", "unknown"),
                "fetched_at": snap.get("fetched_at"),
            },
        },
    }
    if snap.get("source") == "synthetic_curated":
        payload["synthetic_data"] = True
    return {k: v for k, v in payload.items() if v is not None or k == "lineage"}


class RecordedProvider(BaseProvider):
    """Prepares a payload from a recorded snapshot with honest quality marks
    and PROVIDER_LIMITATION degradations from the capability matrix."""
    profile = "yfinance_pragmatic"

    def __init__(self, snapshot_path: str):
        self.snapshot_path = snapshot_path

    def prepare(self, payload_overrides: dict = None) -> ProviderResult:
        snap = load_snapshot(self.snapshot_path)
        payload = map_snapshot_to_payload(snap)
        payload["provider_profile"] = self.profile
        payload.update(payload_overrides or {})
        quality, degradations = {}, []
        for field, q in YFINANCE_CAPABILITY.items():
            if q == "missing" and payload.get(field) is None:
                quality[field] = "missing"
                degradations.append(
                    f"PROVIDER_LIMITATION: '{field}' not suppliable by "
                    f"yfinance per SWS definition")
        for k, v in payload.items():
            if v is not None and k not in ("lineage", "provider_profile"):
                quality.setdefault(k, quality_for_field(self.profile, k))
        if payload.get("synthetic_data"):
            degradations.append(
                "SYNTHETIC_CURATED_DATA: recorded snapshot contains synthetic "
                "values supplied for construction/testing, not real market data")
        degradations.append(
            "yfinance_pragmatic outputs are pragmatic approximations, "
            "not a faithful replication of the SWS methodology")
        return ProviderResult(payload=payload, field_quality=quality,
                              degradations=degradations)
