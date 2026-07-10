"""Inject curated market/industry averages into a company payload (B3).

The 2026-07-10 real calibration found 9 of ~19 UNKNOWN checks per ticker
caused by missing industry_averages: the averages builder existed and the
operator could produce a snapshot from a numerics-populated universe, but no
payload path consumed it — every live payload carried
PROVIDER_LIMITATION for market/industry averages.

Governance:
- Snapshots whose meta.source contains 'synthetic' are REFUSED (stop
  condition 6: synthetic/demo data must never flow as curated). The operator
  must build the snapshot from a real, numerics-populated universe
  (create-curated-universe-from-yfinance -> build-averages).
- Injected lineage is provider=curated_averages, source_quality=approximation
  (the universe numerics come from yfinance), source_class=E2.
- Industry matching is exact against the snapshot's industry keys; when the
  ticker's industry has no entry, only market averages are injected and an
  INDUSTRY_AVERAGES_NOT_FOUND warning is emitted — industry checks stay
  honestly UNKNOWN rather than borrowing a wrong peer group.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CURATED_AVERAGES_PROVIDER = "curated_averages"


def load_averages_snapshot(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _lineage(meta: dict[str, Any], transform: str) -> dict[str, Any]:
    return {
        "provider": CURATED_AVERAGES_PROVIDER,
        "source_id": CURATED_AVERAGES_PROVIDER,
        "source_field": transform,
        "source_quality": "approximation",
        "source_class": "E2",
        "tier": "curated",
        "as_of": meta.get("industry_averages_as_of"),
        "transform": transform,
    }


def apply_averages_snapshot(
    payload: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    industry: str | None = None,
) -> dict[str, Any]:
    """Inject averages in place; return a transparent report.

    ``industry`` defaults to the payload's own industry field. Existing
    non-null payload averages are preserved (operator/manual data wins) and
    reported as skipped.
    """
    report: dict[str, Any] = {
        "status": "PASS", "reason_code": "AVERAGES_INJECTED",
        "applied_fields": [], "skipped_existing": [], "warnings": [],
        "industry_requested": None, "industry_matched": None,
    }
    meta = snapshot.get("meta") or {}
    source = str(meta.get("source") or "")
    if "synthetic" in source.lower() or "demo" in source.lower():
        report["status"] = "FAIL"
        report["reason_code"] = "SYNTHETIC_AVERAGES_REFUSED"
        report["warnings"].append(
            f"SYNTHETIC_AVERAGES_REFUSED: snapshot meta.source={source!r}; synthetic/demo "
            "averages must never be injected as curated (governance stop condition). "
            "Build the snapshot from a real numerics-populated universe.")
        return report

    payload.setdefault("lineage", {}).setdefault("field_lineage", {})
    lineage = payload["lineage"]["field_lineage"]
    warnings = payload.setdefault("builder_warnings", [])

    market = snapshot.get("market") or {}
    if market:
        if payload.get("market_averages") is not None:
            report["skipped_existing"].append("market_averages")
        else:
            payload["market_averages"] = dict(market)
            lineage["market_averages"] = _lineage(meta, "curated_averages_market")
            report["applied_fields"].append("market_averages")

    industry_name = industry or payload.get("industry")
    report["industry_requested"] = industry_name
    industries = snapshot.get("industries") or {}
    entry = industries.get(industry_name) if industry_name else None
    if entry:
        report["industry_matched"] = industry_name
        if payload.get("industry_averages") is not None:
            report["skipped_existing"].append("industry_averages")
        else:
            payload["industry_averages"] = dict(entry)
            lineage["industry_averages"] = _lineage(meta, f"curated_averages_industry:{industry_name}")
            report["applied_fields"].append("industry_averages")
    else:
        msg = (f"INDUSTRY_AVERAGES_NOT_FOUND: industry {industry_name!r} has no entry in the "
               f"averages snapshot ({len(industries)} industries available); industry-relative "
               "checks stay UNKNOWN rather than borrowing a wrong peer group")
        report["warnings"].append(msg)
        warnings.append(msg)

    if meta.get("industry_averages_as_of") and payload.get("industry_averages_as_of") is None:
        payload["industry_averages_as_of"] = meta["industry_averages_as_of"]

    if report["applied_fields"]:
        warnings.append(
            f"CURATED_AVERAGES_INJECTED: {', '.join(report['applied_fields'])} from curated "
            f"averages snapshot (approximation/E2, as_of {meta.get('industry_averages_as_of')})")
    else:
        report["status"] = "PASS_WITH_LIMITATIONS"
        report["reason_code"] = "AVERAGES_NOT_INJECTED"
    payload["builder_warnings"] = list(dict.fromkeys(warnings))
    return report
