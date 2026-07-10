"""Curated rates injection for provider payloads (P1.2-cal, backlog B1).

Real-data calibration (2026-07-10, 10 tickers) surfaced a wiring bug: the
real-dashboard-bootstrap accepted --bond-csv and --erp-json but used them only
to emit warnings — the live provider payload never received the curated
risk-free rate or ERP, so ``risk_free_rate_10y_5y_avg`` stayed a
critical_missing_input even with a valid curated CSV present.

This module builds mapper-format override specs from the curated rate files
so any payload path (live bootstrap, CLI) can inject them with honest lineage:

- provider is ``curated_rates`` (not mislabeled ``manual_override``);
- source_quality is ``assumption`` and source_class ``E2`` per the
  established doctrine for curated rates (they are operator-curated
  assumptions, not observed company facts);
- missing/unreadable sources produce warnings and NO override — the field
  stays honestly MISSING/UNKNOWN, never silently defaulted.
"""
from __future__ import annotations

import os
from typing import Any

from sws_engine.rates.rates import bond_10y_5y_average, load_erp
from sws_engine.sources.staleness import mark_lineage_stale, staleness_check

CURATED_RATES_PROVIDER = "curated_rates"


def build_curated_rates_overrides(
    bond_csv: str,
    erp_json: str,
    *,
    country: str,
    valuation_date: str,
) -> dict[str, Any]:
    """Return {"overrides": mapper-format dict, "warnings": [...], "meta": {...}}.

    Only fields whose curated value resolves are included; everything else is
    reported in warnings and left for the payload to mark MISSING.
    """
    overrides: dict[str, Any] = {}
    warnings: list[str] = []
    meta: dict[str, Any] = {"country": country, "valuation_date": valuation_date}

    if bond_csv and os.path.exists(bond_csv):
        rf = bond_10y_5y_average(bond_csv, country, valuation_date)
        meta["risk_free"] = rf
        if rf.get("value") is not None:
            spec = {
                "value": rf["value"],
                "source_quality": "assumption",
                "source_class": "E2",
                "provider": CURATED_RATES_PROVIDER,
                "transform": "curated_rates_injection_bond_10y_5y_avg",
                "as_of": rf.get("as_of") or valuation_date,
            }
            # P2.3-enf: the 5y average window ends at valuation date by
            # construction; the freshness contract applies to the NEWEST
            # observation in the CSV, which is what must not be stale.
            latest_obs = _latest_observation_date(bond_csv, country)
            check = staleness_check(latest_obs, source_id="bond_10y_5y_avg_curated",
                                    valuation_date=valuation_date)
            if check["warning"]:
                warnings.append(check["warning"])
            mark_lineage_stale(spec, check)
            overrides["risk_free_rate_10y_5y_avg"] = spec
        else:
            warnings.append(
                "CURATED_RATES_NO_OBSERVATIONS: bond CSV present but no usable "
                f"{country} observations in the 5y window ending {valuation_date}; "
                "risk_free_rate_10y_5y_avg stays MISSING")
    else:
        warnings.append(
            f"CURATED_RATES_FILE_MISSING: '{bond_csv}' not found; "
            "risk_free_rate_10y_5y_avg stays MISSING")

    if erp_json and os.path.exists(erp_json):
        erp = load_erp(erp_json, country)
        meta["erp"] = erp
        expires_at = _erp_expires_at(erp_json)
        if expires_at and str(valuation_date) > str(expires_at):
            # P2.3-enf: expiry is a curation contract — a lapsed ERP is
            # REFUSED (mirrors the estimates-pack behavior); the field stays
            # honestly MISSING until the operator re-curates.
            warnings.append(
                f"CURATED_ERP_EXPIRED: erp_curated expired {expires_at} < valuation date "
                f"{valuation_date}; equity_risk_premium stays MISSING until re-curated "
                "(next Damodaran semiannual update)")
        elif erp.get("value") is not None:
            spec = {
                "value": erp["value"],
                "source_quality": "assumption",
                "source_class": "E2",
                "provider": CURATED_RATES_PROVIDER,
                "transform": "curated_rates_injection_erp",
                "as_of": erp.get("as_of") or valuation_date,
            }
            check = staleness_check(erp.get("as_of"), source_id="erp_curated",
                                    valuation_date=valuation_date)
            if check["warning"]:
                warnings.append(check["warning"])
            mark_lineage_stale(spec, check)
            overrides["equity_risk_premium"] = spec
        else:
            warnings.append(
                f"CURATED_ERP_NO_COUNTRY_ENTRY: ERP file present but no {country} "
                "entry; equity_risk_premium stays MISSING")
    else:
        warnings.append(
            f"CURATED_ERP_FILE_MISSING: '{erp_json}' not found; "
            "equity_risk_premium stays MISSING")

    return {"overrides": overrides, "warnings": warnings, "meta": meta}

def _latest_observation_date(bond_csv: str, country: str) -> str | None:
    """Newest observation date for the country in the curated bond CSV."""
    import csv
    latest: str | None = None
    try:
        with open(bond_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("country") != country:
                    continue
                d = row.get("date")
                if d and (latest is None or d > latest):
                    latest = d
    except OSError:
        return None
    return latest


def _erp_expires_at(erp_json: str) -> str | None:
    import json as _json
    try:
        with open(erp_json, encoding="utf-8") as fh:
            return (_json.load(fh) or {}).get("expires_at")
    except (OSError, ValueError):
        return None
