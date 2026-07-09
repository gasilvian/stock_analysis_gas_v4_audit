"""Industry & market averages builder (SPEC section 7).

Supports both the original synthetic universe and a real-universe workflow.
Every snapshot records: level, metric type, source date, provider/source,
minimum universe count and excluded instruments. PB is aggregated only when
it can be reconstructed from tangible book value; it is never approximated
from generic book value.

Fallback hierarchy for an industry metric:
  industry+country -> industry+region -> industry+global -> market
The legacy output shape is preserved: ``snapshot['market']`` and
``snapshot['industries'][industry]`` remain available for existing payload
builders. Additional detail is available under ``snapshot['levels']``.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date
from typing import Iterable

EXCLUDED_KINDS = ("etf", "fund", "dr", "secondary_listing")
NUMERIC = (
    "price", "eps", "shares_outstanding", "total_assets",
    "intangible_assets", "total_liabilities", "market_cap",
    "net_income_growth", "revenue_growth", "eps_growth", "roa",
    "dividend_yield",
)
DEFAULT_REGION = "global"
DEFAULT_COUNTRY = "unknown"


def load_universe(csv_path: str) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for k in NUMERIC:
                v = row.get(k, "")
                row[k] = float(v) if v not in ("", None) else None
            row.setdefault("country", DEFAULT_COUNTRY)
            row.setdefault("region", DEFAULT_REGION)
            row.setdefault("provider_profile", "yfinance_pragmatic")
            rows.append(row)
    return rows


def save_universe_coverage(rows: list[dict], out_path: str, min_required_fields: Iterable[str] = ("price", "eps", "shares_outstanding")) -> str:
    """Write a coverage report per ticker for a real-universe CSV.

    The report is intentionally simple JSON so it can be inspected before
    using a universe in daily averages. It does not fetch data; it validates
    that the curated universe row has enough fields for useful aggregates.
    """
    required = tuple(min_required_fields)
    report = []
    for row in rows:
        missing = [f for f in required if row.get(f) in (None, "")]
        report.append({
            "ticker": row.get("ticker"),
            "country": row.get("country", DEFAULT_COUNTRY),
            "region": row.get("region", DEFAULT_REGION),
            "industry": row.get("industry", "unknown"),
            "missing_required_fields": missing,
            "coverage_ok": not missing,
        })
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"rows": report}, fh, indent=2)
    return out_path


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _percentile(vals, p):
    s = sorted(vals)
    if not s:
        return None
    if len(s) == 1:
        return s[0]
    idx = p * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _weighted_mean(pairs):
    known = [(w, v) for w, v in pairs if v is not None and w]
    if not known:
        return None
    tw = sum(w for w, _ in known)
    return sum(w * v for w, v in known) / tw if tw else None


def _pe(row):
    if row["price"] and row["eps"] and row["eps"] > 0:
        return row["price"] / row["eps"]
    return None


def _pb_tangible(row):
    ta, ia, tl, sh = (row["total_assets"], row["intangible_assets"], row["total_liabilities"], row["shares_outstanding"])
    if None in (ta, ia, tl, sh) or not sh or not row["price"]:
        return None
    tbvps = (ta - ia - tl) / sh
    return row["price"] / tbvps if tbvps > 0 else None


def _aggregate(rows, *, level: str = "market", source: str = "curated_universe"):
    rows = list(rows)
    pes = [_pe(r) for r in rows]
    pes = [p for p in pes if p is not None]
    pbs = [_pb_tangible(r) for r in rows]
    pb_known = [p for p in pbs if p is not None]
    yields = [r["dividend_yield"] for r in rows if r["dividend_yield"] is not None]
    return {
        "level": level,
        "source": source,
        "pe_median_profitable": _median(pes),
        "pb_average": (sum(pb_known) / len(pb_known)) if pb_known else None,
        "pb_excluded_no_tangible_bv": sum(1 for p in pbs if p is None),
        "eps_growth": _median([r["eps_growth"] for r in rows if r["eps_growth"] is not None]),
        "roa": _median([r["roa"] for r in rows if r["roa"] is not None]),
        "net_income_growth": _weighted_mean([(r["market_cap"], r["net_income_growth"]) for r in rows]),
        "revenue_growth": _weighted_mean([(r["market_cap"], r["revenue_growth"]) for r in rows]),
        "dividend_yield_p10": _percentile(yields, 0.10),
        "dividend_yield_p25": _percentile(yields, 0.25),
        "dividend_yield_p75": _percentile(yields, 0.75),
        "universe_count": len(rows),
    }


def _eligible_rows(universe_rows):
    return [r for r in universe_rows if (r.get("kind") or "stock").lower() not in EXCLUDED_KINDS]


def _excluded_rows(universe_rows):
    return [r for r in universe_rows if (r.get("kind") or "stock").lower() in EXCLUDED_KINDS]


def _filter(rows, **eq):
    out = rows
    for k, v in eq.items():
        out = [r for r in out if (r.get(k) or "unknown") == v]
    return out


def _with_macro(market_agg: dict, savings_rate, cpi):
    if savings_rate is not None:
        market_agg["savings_rate"] = savings_rate
    if cpi is not None:
        market_agg["cpi"] = cpi
    return market_agg


def _choose_industry_level(*, eligible, industry, country, region, market_agg, min_universe_count, warnings, source):
    country_rows = _filter(eligible, industry=industry, country=country)
    if len(country_rows) >= min_universe_count:
        agg = _aggregate(country_rows, level="industry_country", source=source)
        agg.update({"fallback_level": "industry_country", "country": country, "region": region, "industry": industry})
        return agg

    region_rows = _filter(eligible, industry=industry, region=region)
    if len(region_rows) >= min_universe_count:
        agg = _aggregate(region_rows, level="industry_region", source=source)
        agg.update({"fallback_level": "industry_region", "country": country, "region": region, "industry": industry, "universe_count_industry_country": len(country_rows)})
        warnings.append(f"FALLBACK: industry '{industry}' country '{country}' has {len(country_rows)} instruments (< {min_universe_count}); region-level averages used")
        return agg

    global_rows = _filter(eligible, industry=industry)
    if len(global_rows) >= min_universe_count:
        agg = _aggregate(global_rows, level="industry_global", source=source)
        agg.update({"fallback_level": "industry_global", "country": country, "region": region, "industry": industry, "universe_count_industry_country": len(country_rows), "universe_count_industry_region": len(region_rows)})
        warnings.append(f"FALLBACK: industry '{industry}' region '{region}' has {len(region_rows)} instruments (< {min_universe_count}); global industry averages used")
        return agg

    agg = dict(market_agg)
    agg.update({"fallback_level": "market", "country": country, "region": region, "industry": industry, "universe_count_industry_country": len(country_rows), "universe_count_industry_region": len(region_rows), "universe_count_industry_global": len(global_rows)})
    warnings.append(f"FALLBACK: industry '{industry}' has {len(global_rows)} global instruments (< {min_universe_count}); market-level averages used")
    return agg


def build_averages(universe_rows, as_of=None, min_universe_count=5, savings_rate=None, cpi=None, source="synthetic_curated", market_name=None):
    """Build market/industry averages with country->region->global fallback.

    Legacy callers can keep using snapshot['industries'][industry]. New callers
    may use snapshot['levels']['industry_country']["<country>|<industry>"] for
    explicit fallbacks.
    """
    as_of = as_of or date.today().isoformat()
    eligible = _eligible_rows(universe_rows)
    excluded = [r.get("ticker") for r in _excluded_rows(universe_rows)]

    market = _with_macro(_aggregate(eligible, level="market", source=source), savings_rate, cpi)
    warnings = []
    levels = {"industry_country": {}, "industry_region": {}, "industry_global": {}, "country": {}, "region": {}}

    countries = sorted({r.get("country", DEFAULT_COUNTRY) for r in eligible}) or [DEFAULT_COUNTRY]
    regions = sorted({r.get("region", DEFAULT_REGION) for r in eligible}) or [DEFAULT_REGION]
    industries_set = sorted({r.get("industry") or "unknown" for r in eligible})

    for country in countries:
        rows = _filter(eligible, country=country)
        if rows:
            levels["country"][country] = _aggregate(rows, level="country", source=source)
    for region in regions:
        rows = _filter(eligible, region=region)
        if rows:
            levels["region"][region] = _aggregate(rows, level="region", source=source)
    for industry in industries_set:
        rows = _filter(eligible, industry=industry)
        levels["industry_global"][industry] = _aggregate(rows, level="industry_global", source=source)
        for region in regions:
            rrows = _filter(eligible, industry=industry, region=region)
            if rrows:
                levels["industry_region"][f"{region}|{industry}"] = _aggregate(rrows, level="industry_region", source=source)
        for country in countries:
            crows = _filter(eligible, industry=industry, country=country)
            region = crows[0].get("region", DEFAULT_REGION) if crows else DEFAULT_REGION
            levels["industry_country"][f"{country}|{industry}"] = _choose_industry_level(
                eligible=eligible, industry=industry, country=country, region=region,
                market_agg=market, min_universe_count=min_universe_count, warnings=warnings, source=source)

    # Legacy industries: choose the best aggregate for the dominant country/region
    # present in the universe, preserving older callers.
    legacy_industries = {}
    dominant_country = countries[0]
    for industry in industries_set:
        key = f"{dominant_country}|{industry}"
        legacy = dict(levels["industry_country"].get(key) or levels["industry_global"].get(industry) or market)
        # Backward-compatible labels for older Phase 3 tests/reports.
        if legacy.get("fallback_level") in {"industry_country", "industry_region", "industry_global"}:
            legacy["fallback_level"] = "industry"
        legacy_industries[industry] = legacy

    return {
        "meta": {
            "industry_averages_as_of": as_of,
            "market": market_name,
            "source": source,
            "min_universe_count": min_universe_count,
            "excluded_instruments": excluded,
            "fallback_hierarchy": ["industry_country", "industry_region", "industry_global", "market"],
            "provider_profile": "yfinance_pragmatic" if "yfinance" in source else "curated_or_synthetic",
            "metric_definitions": {
                "pe_median_profitable": "median PE over companies with EPS>0",
                "pb_average": "mean PB from tangible book value only; generic book value excluded",
                "net_income_growth": "market-cap weighted mean",
                "revenue_growth": "market-cap weighted mean",
                "eps_growth": "median",
                "roa": "median",
                "dividend_yield_pXX": "linear-interpolated percentile",
            },
        },
        "market": market,
        "industries": legacy_industries,
        "levels": levels,
        "warnings": list(dict.fromkeys(warnings)),
    }


def save_snapshot(snapshot: dict, out_dir: str, market_name: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"averages_{market_name}_{snapshot['meta']['industry_averages_as_of']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    return path
