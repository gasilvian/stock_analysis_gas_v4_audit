"""Create a pragmatic curated universe CSV from live yfinance metadata.

The resulting file is explicitly marked as yfinance-derived and requiring
operator review. It never contains invented sector/industry values: missing
metadata becomes UNKNOWN plus a warning in the creation report.

This helper does not force production-readiness to PASS. The source registry
may still legitimately require manual review of the curated universe.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List

SOURCE_TAG = "yfinance_live_pragmatic_curated"
NOTES_TAG = "operator-reviewed yfinance metadata required before production readiness"

FOOTER = (
    "Internal, non-commercial, educational use only. Not investment advice. "
    "Not the live Simply Wall St model. Methodology attribution: Simply Wall St "
    "public Company-Analysis-Model / Portfolio-Analysis-Model repositories "
    "(CC BY-NC-SA 4.0)."
)

COLUMNS = ["ticker", "exchange", "market", "country", "region", "sector",
           "industry", "currency", "company_type", "include", "source",
           "source_as_of", "notes"]

# Deterministic, factual country->region lookup (metadata, not an analytical
# input). Anything not listed stays UNKNOWN with a warning.
_COUNTRY_REGION = {
    "United States": "North America",
    "Canada": "North America",
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Netherlands": "Europe",
    "Switzerland": "Europe",
    "Japan": "Asia",
    "China": "Asia",
    "Australia": "Oceania",
}

# Sectors whose engine company_type cannot be inferred without operator
# review (bank vs insurance vs REIT routing changes the check set).
_REVIEW_SECTORS = {"Financial Services", "Real Estate"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch_info(ticker: str, refresh: bool = False) -> Dict[str, Any]:
    """Fetch raw yfinance metadata; monkeypatched in offline tests."""
    from sws_engine.providers.yfinance_live import YFinanceLiveProvider
    provider = YFinanceLiveProvider(refresh=refresh)
    provider._require_yfinance()
    t = provider.yf.Ticker(ticker)
    info: Dict[str, Any] = {}
    try:
        raw = t.info
        if isinstance(raw, dict):
            info.update(raw)
    except Exception:
        pass
    try:
        fast = getattr(t, "fast_info", None)
        if fast is not None:
            for key in ("currency", "exchange"):
                try:
                    val = fast[key] if hasattr(fast, "__getitem__") else getattr(fast, key, None)
                except Exception:
                    val = None
                if val and not info.get(key):
                    info[key] = val
    except Exception:
        pass
    return info


def _row_from_info(ticker: str, market: str, info: Dict[str, Any],
                   warnings: List[str]) -> Dict[str, Any]:
    def _get(key: str, label: str) -> str:
        val = info.get(key)
        if val in (None, "", []):
            warnings.append(f"{ticker}: missing '{label}' from yfinance metadata; set to UNKNOWN")
            return "UNKNOWN"
        return str(val)

    country = _get("country", "country")
    region = _COUNTRY_REGION.get(country, "UNKNOWN")
    if region == "UNKNOWN" and country != "UNKNOWN":
        warnings.append(f"{ticker}: country '{country}' has no region mapping; region set to UNKNOWN")
    sector = _get("sector", "sector")
    if sector == "UNKNOWN":
        company_type = "UNKNOWN"
        warnings.append(f"{ticker}: company_type cannot be derived without sector; set to UNKNOWN")
    elif sector in _REVIEW_SECTORS:
        company_type = "UNKNOWN"
        warnings.append(
            f"{ticker}: sector '{sector}' requires operator review to classify "
            "company_type (bank/insurance/REIT routing); set to UNKNOWN")
    else:
        company_type = "non_financial"
    return {
        "ticker": ticker,
        "exchange": _get("exchange", "exchange"),
        "market": market,
        "country": country,
        "region": region,
        "sector": sector,
        "industry": _get("industry", "industry"),
        "currency": _get("currency", "currency"),
        "company_type": company_type,
        "include": "true",
        "source": SOURCE_TAG,
        "source_as_of": date.today().isoformat(),
        "notes": NOTES_TAG,
    }


def create_curated_universe(
    *,
    tickers: str | List[str],
    market: str = "US",
    output_path: str = "data/real_sources/universe/universe_US_curated.csv",
    refresh: bool = False,
    report_path: str = "out/real_dashboard_bootstrap/universe_creation_report.md",
) -> Dict[str, Any]:
    if isinstance(tickers, str):
        items = [t.strip() for t in tickers.split(",") if t.strip()]
    else:
        items = [str(t).strip() for t in tickers if str(t).strip()]
    if not items:
        raise ValueError("create-curated-universe-from-yfinance requires at least one ticker")

    warnings: List[str] = []
    rows: List[Dict[str, Any]] = []
    failed: List[Dict[str, str]] = []
    for ticker in items:
        try:
            info = _fetch_info(ticker, refresh=refresh)
        except Exception as exc:
            failed.append({"ticker": ticker, "error": f"{exc.__class__.__name__}: {exc}"})
            continue
        rows.append(_row_from_info(ticker, market, info, warnings))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary = {
        "generated_at": _utc_now(),
        "output_path": output_path,
        "market": market,
        "tickers_requested": items,
        "rows_written": len(rows),
        "tickers_failed": failed,
        "warnings": warnings,
        "source": SOURCE_TAG,
        "production_readiness_note": (
            "This curated file is yfinance-derived and pragmatic. The source "
            "registry may still require operator review; production-readiness "
            "may legitimately remain NOT_READY."
        ),
    }

    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(_render_report_md(summary, rows))
    summary["report_path"] = report_path
    return summary


def _render_report_md(summary: Dict[str, Any], rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# Universe Creation Report (yfinance pragmatic curated)",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Output file: `{summary['output_path']}`",
        f"- Market: {summary['market']}",
        f"- Rows written: {summary['rows_written']}",
        f"- Source: `{summary['source']}`",
        "",
        f"> {summary['production_readiness_note']}",
        "",
        "## Rows",
        "",
        "| Ticker | Exchange | Country | Region | Sector | Industry | Currency | company_type |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['ticker']} | {r['exchange']} | {r['country']} | {r['region']} | "
            f"{r['sector']} | {r['industry']} | {r['currency']} | {r['company_type']} |")
    lines += ["", "## Warnings", ""]
    if summary["warnings"]:
        lines += [f"- {w}" for w in summary["warnings"]]
    else:
        lines.append("- none")
    if summary["tickers_failed"]:
        lines += ["", "## Failed tickers", ""]
        lines += [f"- {f['ticker']}: {f['error']}" for f in summary["tickers_failed"]]
    lines += ["", "---", "", FOOTER, ""]
    return "\n".join(lines)


def summary_json(summary: Dict[str, Any]) -> str:
    return json.dumps(summary, indent=2)
