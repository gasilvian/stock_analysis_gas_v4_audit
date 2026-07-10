"""Manual analyst-estimates pack: operator-transcribed forward data (B4).

The remaining UNKNOWN mass after SEC + curated averages (7 checks on the
calibrated AAPL ladder) is the analyst-estimates family. Per the data-source
inventory there is NO honest free API for the SWS weighted format (forecast
year + analyst count); the designed workflow is manual transcription from a
platform the operator can read (TIKR / Koyfin / TradingView), captured in a
reviewed, expiring JSON pack per ticker.

Pack file: data/real_sources/estimates/{TICKER}_analyst_estimates.json

Recognized payload fields and shapes:
- earnings_estimates: [{"fiscal_year": int, "value": float, "analysts": int}, ...]
  (chronological; feeds the growth resolver's analyst route A)
- fcf_estimates:      [{"fiscal_year": int, "value": float}, ...]
  (feeds the two-stage FCF valuation directly - the SWS-faithful path)
- earnings_growth / revenue_growth: floats (operator-transcribed consensus
  forward growth, feeds FUTURE checks)
- becomes_profitable_in_5y: bool
- analyst_estimates_as_of is set from the pack's source_as_of.

Governance (enforced, not advisory):
- template markers (filename or source containing 'template') are refused;
- review_status must be 'reviewed' (operator approval) or injection is
  refused with ESTIMATES_NOT_REVIEWED;
- expired packs (valuation_date > expires_at) are refused with
  ESTIMATES_EXPIRED — stale forecasts must surface as UNKNOWN, not linger;
- injected lineage is provider=manual_estimates_pack,
  source_quality=assumption, source_class=E3, tier=manual_curated: these are
  transcribed forecasts, never 'exact' data;
- existing non-null payload values are preserved and reported as skipped.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANUAL_ESTIMATES_PROVIDER = "manual_estimates_pack"
RECOGNIZED_SERIES = ("earnings_estimates", "fcf_estimates")
RECOGNIZED_SCALARS = ("earnings_growth", "revenue_growth", "becomes_profitable_in_5y")


def load_estimates_pack(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate(pack: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not pack.get("ticker"):
        problems.append("ticker missing")
    for key in ("source_as_of", "expires_at", "review_status"):
        if not pack.get(key):
            problems.append(f"{key} missing")
    for series_key in RECOGNIZED_SERIES:
        series = pack.get(series_key)
        if series is None:
            continue
        if not isinstance(series, list) or not series:
            problems.append(f"{series_key} must be a non-empty list")
            continue
        years = []
        for i, item in enumerate(series):
            if not isinstance(item, dict) or item.get("value") is None:
                problems.append(f"{series_key}[{i}] needs a numeric 'value'")
                continue
            if series_key == "earnings_estimates" and not item.get("analysts"):
                problems.append(f"{series_key}[{i}] needs 'analysts' (SWS weighted format)")
            if item.get("fiscal_year"):
                years.append(int(item["fiscal_year"]))
        if years and years != sorted(years):
            problems.append(f"{series_key} must be chronological by fiscal_year")
    return problems


def _lineage(pack: dict[str, Any], field: str) -> dict[str, Any]:
    return {
        "provider": MANUAL_ESTIMATES_PROVIDER,
        "source_id": MANUAL_ESTIMATES_PROVIDER,
        "source_field": field,
        "source_quality": "assumption",
        "source_class": "E3",
        "tier": "manual_curated",
        "as_of": pack.get("source_as_of"),
        "transform": f"manual_transcription:{pack.get('source_detail') or pack.get('source') or 'operator'}",
    }


def apply_estimates_pack(
    payload: dict[str, Any],
    pack: dict[str, Any],
    *,
    valuation_date: str,
    require_reviewed: bool = True,
    pack_path: str | Path | None = None,
) -> dict[str, Any]:
    """Inject the pack into the payload in place; return a transparent report."""
    report: dict[str, Any] = {
        "status": "PASS", "reason_code": "ESTIMATES_INJECTED",
        "ticker": pack.get("ticker"), "applied_fields": [],
        "skipped_existing": [], "warnings": [],
    }

    def _refuse(reason: str, message: str) -> dict[str, Any]:
        report["status"] = "FAIL"
        report["reason_code"] = reason
        report["warnings"].append(message)
        return report

    name_l = str(pack_path or "").lower()
    if "template" in name_l or "template" in str(pack.get("source") or "").lower():
        return _refuse("ESTIMATES_TEMPLATE_REFUSED",
                       "ESTIMATES_TEMPLATE_REFUSED: template packs are placeholders and are never injected")
    problems = _validate(pack)
    if problems:
        return _refuse("ESTIMATES_PACK_INVALID",
                       "ESTIMATES_PACK_INVALID: " + "; ".join(problems))
    if pack.get("ticker") and payload.get("ticker") and pack["ticker"] != payload["ticker"]:
        return _refuse("ESTIMATES_TICKER_MISMATCH",
                       f"ESTIMATES_TICKER_MISMATCH: payload {payload.get('ticker')!r} vs pack {pack.get('ticker')!r}")
    if require_reviewed and pack.get("review_status") != "reviewed":
        return _refuse("ESTIMATES_NOT_REVIEWED",
                       f"ESTIMATES_NOT_REVIEWED: review_status={pack.get('review_status')!r}; "
                       "operator must review before injection")
    if str(valuation_date) > str(pack.get("expires_at")):
        return _refuse("ESTIMATES_EXPIRED",
                       f"ESTIMATES_EXPIRED: pack expired {pack.get('expires_at')} < valuation date "
                       f"{valuation_date}; stale forecasts surface as UNKNOWN, re-transcribe first")

    payload.setdefault("lineage", {}).setdefault("field_lineage", {})
    lineage = payload["lineage"]["field_lineage"]
    warnings = payload.setdefault("builder_warnings", [])

    for series_key in RECOGNIZED_SERIES:
        series = pack.get(series_key)
        if series is None:
            continue
        if payload.get(series_key) is not None:
            report["skipped_existing"].append(series_key)
            continue
        payload[series_key] = [
            {k: v for k, v in item.items() if k in ("value", "analysts")}
            for item in series
        ]
        lineage[series_key] = _lineage(pack, series_key)
        report["applied_fields"].append(series_key)

    for scalar_key in RECOGNIZED_SCALARS:
        if scalar_key not in pack or pack.get(scalar_key) is None:
            continue
        if payload.get(scalar_key) is not None:
            report["skipped_existing"].append(scalar_key)
            continue
        payload[scalar_key] = pack[scalar_key]
        lineage[scalar_key] = _lineage(pack, scalar_key)
        report["applied_fields"].append(scalar_key)

    if report["applied_fields"] and payload.get("analyst_estimates_as_of") is None:
        payload["analyst_estimates_as_of"] = pack.get("source_as_of")

    if report["applied_fields"]:
        # Honesty polish: build-time warnings stating an injected field is
        # unavailable are now contradicted by the pack; drop only those lines.
        stale = tuple(f"{f} not available" for f in report["applied_fields"])
        warnings[:] = [w for w in warnings if not any(s in w for s in stale)]
        warnings.append(
            f"MANUAL_ESTIMATES_INJECTED: {', '.join(report['applied_fields'])} from the operator "
            f"estimates pack (assumption/E3, as_of {pack.get('source_as_of')}, "
            f"expires {pack.get('expires_at')})")
    else:
        report["status"] = "PASS_WITH_LIMITATIONS"
        report["reason_code"] = "ESTIMATES_NOTHING_TO_INJECT"
    payload["builder_warnings"] = list(dict.fromkeys(warnings))
    return report


def apply_estimates_from_dir(
    payload: dict[str, Any],
    estimates_dir: str | Path,
    *,
    valuation_date: str,
    require_reviewed: bool = True,
) -> dict[str, Any]:
    """Locate {ticker}_analyst_estimates.json under estimates_dir and inject.

    Missing pack is an honest no-op (ESTIMATES_PACK_NOT_FOUND) — the fields
    stay MISSING/UNKNOWN, never guessed.
    """
    ticker = str(payload.get("ticker") or "").upper()
    candidate = Path(estimates_dir) / f"{ticker}_analyst_estimates.json"
    if not candidate.exists():
        return {
            "status": "PASS_WITH_LIMITATIONS",
            "reason_code": "ESTIMATES_PACK_NOT_FOUND",
            "ticker": ticker, "applied_fields": [], "skipped_existing": [],
            "warnings": [f"ESTIMATES_PACK_NOT_FOUND: no {candidate.name} under {estimates_dir}"],
        }
    return apply_estimates_pack(
        payload, load_estimates_pack(candidate),
        valuation_date=valuation_date, require_reviewed=require_reviewed,
        pack_path=candidate)
