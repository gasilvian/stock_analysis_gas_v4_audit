"""Merge SEC statement-snapshot updates into a company payload (P1.3b, B4/B8).

Until this module, the SEC foundation (P0.3) was an unintegrated silo: the
refresh-sec-financials workflow produced normalized ``payload_updates``
artifacts that nothing consumed, so live payloads stayed 100% yfinance even
when official filings were cached locally — the top data-confidence complaint
of the 2026-07-10 real calibration (confidence D/E across all ten tickers).

Precedence doctrine implemented here (documented, not silent):
- SEC official filings (exact/E0/official_filing) take precedence over
  provider (yfinance_pragmatic) values for the statement fields they cover —
  "SEC ramane precedent pe orice camp US".
- Curated rates are disjoint fields and unaffected.
- Manual operator overrides applied AFTER the merge (the existing
  merge-overrides CLI step) win over SEC, because a deliberate operator
  decision outranks any automated source.
- A SEC field with source_quality=missing or a null value NEVER overwrites a
  present provider value — enrichment can only add official facts, never
  degrade or blank the base.

Conflict visibility (seed of the B5 conflict detector): whenever the base
payload already carried a materially different value for a field the merge
replaces, a conflict record {field, base value+provider, sec value, relative
difference, resolution=sec_precedence} is appended to
``payload["source_conflicts"]`` and summarized in builder_warnings. Nothing
is resolved silently.

The base payload's ``provider_profile`` is intentionally preserved: an
enriched yfinance payload remains yfinance_pragmatic, with the per-field
lineage (not the profile) carrying the official_filing truth. Flipping the
profile would hide the remaining yfinance degradation on unenriched fields.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SEC_META_FIELDS = {
    "ticker", "provider_profile", "valuation_date", "exchange",
    "lineage", "sec_mapping_warnings",
}
DEFAULT_CONFLICT_TOLERANCE = 0.005  # 0.5% relative difference


def load_sec_payload_updates(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _relative_diff(base: float, new: float) -> float:
    denom = max(abs(base), abs(new), 1e-12)
    return abs(base - new) / denom


def _values_conflict(base: Any, new: Any, tolerance: float) -> tuple[bool, float | None]:
    if isinstance(base, (int, float)) and isinstance(new, (int, float)) \
            and not isinstance(base, bool) and not isinstance(new, bool):
        rel = _relative_diff(float(base), float(new))
        return rel > tolerance, rel
    return base != new, None


def apply_sec_payload_updates(
    payload: dict[str, Any],
    sec_updates: Mapping[str, Any],
    *,
    conflict_tolerance: float = DEFAULT_CONFLICT_TOLERANCE,
    precedence: list[str] | None = None,
) -> dict[str, Any]:
    """Apply SEC payload updates in place; return a transparent merge report.

    B5: conflict resolution is registry-driven. The winner between
    sec_companyfacts and the base field's provider comes from the precedence
    chain (config/source_registry.yaml); when the pair is not covered by the
    chain, the field is set to UNKNOWN (None + missing lineage) rather than
    silently picking either side. On ticker mismatch nothing is mutated.
    """
    from sws_engine.sources.conflict_detector import load_precedence, resolve_precedence
    chain = precedence if precedence is not None else load_precedence()
    report: dict[str, Any] = {
        "status": "PASS", "reason_code": "SEC_ENRICHMENT_APPLIED",
        "ticker": payload.get("ticker"),
        "applied_fields": [], "skipped_missing": [], "conflicts": [],
        "unresolved_fields": [],
        "warnings": [],
    }
    sec_ticker = sec_updates.get("ticker")
    if sec_ticker and payload.get("ticker") and sec_ticker != payload.get("ticker"):
        report["status"] = "FAIL"
        report["reason_code"] = "SEC_TICKER_MISMATCH"
        report["warnings"].append(
            f"SEC_TICKER_MISMATCH: payload ticker {payload.get('ticker')!r} vs "
            f"SEC updates ticker {sec_ticker!r}; merge aborted, payload untouched")
        return report

    sec_lineage = ((sec_updates.get("lineage") or {}).get("field_lineage") or {})
    payload.setdefault("lineage", {}).setdefault("field_lineage", {})
    base_lineage = payload["lineage"]["field_lineage"]

    for field, value in sec_updates.items():
        if field in SEC_META_FIELDS:
            continue
        field_lin = dict(sec_lineage.get(field) or {})
        if value is None or str(field_lin.get("source_quality", "")).lower() == "missing":
            report["skipped_missing"].append({
                "field": field,
                "reason_code": field_lin.get("reason_code", "SEC_VALUE_MISSING"),
            })
            continue  # never blank or downgrade a base value with a SEC gap

        base_value = payload.get(field)
        if base_value is not None:
            conflicting, rel = _values_conflict(base_value, value, conflict_tolerance)
            if conflicting:
                base_lin = base_lineage.get(field) or {}
                base_provider = base_lin.get("provider") or payload.get("provider_profile") or "unknown"
                winner = resolve_precedence("sec_companyfacts", str(base_provider), chain)
                record = {
                    "field": field,
                    "base_value": base_value,
                    "base_provider": base_provider,
                    "sec_value": value,
                    "relative_diff": round(rel, 6) if rel is not None else None,
                }
                if winner is None:
                    # Doctrine: no precedence rule for the pair -> UNKNOWN,
                    # never a silent pick between disagreeing sources.
                    record["resolution"] = "unresolved_no_precedence_rule"
                    report["conflicts"].append(record)
                    report["unresolved_fields"].append(field)
                    payload[field] = None
                    base_lineage[field] = {
                        "provider": "conflict_detector",
                        "source_field": field,
                        "source_quality": "missing",
                        "source_class": "E0",
                        "reason_code": "SOURCE_CONFLICT_UNRESOLVED",
                        "detail": f"{base_provider} vs sec_companyfacts, no precedence rule",
                    }
                    continue
                if winner != "sec_companyfacts":
                    record["resolution"] = f"precedence:{winner}"
                    report["conflicts"].append(record)
                    continue  # base wins per registry; SEC value not applied
                record["resolution"] = "sec_precedence"
                report["conflicts"].append(record)
        payload[field] = value
        if not field_lin:
            field_lin = {
                "provider": "sec_companyfacts", "source_field": field,
                "source_quality": "exact", "source_class": "E0",
                "tier": "official_filing",
            }
        base_lineage[field] = field_lin
        report["applied_fields"].append(field)

    warnings = payload.setdefault("builder_warnings", [])
    if report["applied_fields"]:
        warnings.append(
            f"SEC_ENRICHMENT_APPLIED: {len(report['applied_fields'])} fields replaced "
            "with SEC CompanyFacts values (official_filing/exact/E0); provider_profile "
            "unchanged, per-field lineage carries the source of truth")
    else:
        report["status"] = "PASS_WITH_LIMITATIONS"
        report["reason_code"] = "SEC_ENRICHMENT_NO_FIELDS"
    if report["conflicts"]:
        payload.setdefault("source_conflicts", []).extend(report["conflicts"])
        warnings.append(
            f"SOURCE_CONFLICT_DETECTED: {len(report['conflicts'])} field(s) where the "
            "provider value differed materially from the SEC filing; resolved by "
            "documented sec_precedence, details in source_conflicts")
        report["warnings"].append("conflicts recorded in payload.source_conflicts")
    payload["builder_warnings"] = list(dict.fromkeys(warnings))
    return report


def merge_sec_updates_from_dir(
    payload: dict[str, Any],
    sec_dir: str | Path,
    *,
    conflict_tolerance: float = DEFAULT_CONFLICT_TOLERANCE,
) -> dict[str, Any]:
    """Locate ``{ticker}_sec_payload_updates.json`` under sec_dir and merge it.

    Missing artifact is an honest no-op with reason SEC_UPDATES_NOT_FOUND —
    the payload is returned exactly as it was, never guessed at.
    """
    ticker = str(payload.get("ticker") or "").upper()
    candidates = [
        Path(sec_dir) / f"{ticker}_sec_payload_updates.json",
        Path(sec_dir) / "normalized" / f"{ticker}_sec_payload_updates.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return apply_sec_payload_updates(
                payload, load_sec_payload_updates(candidate),
                conflict_tolerance=conflict_tolerance)
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "reason_code": "SEC_UPDATES_NOT_FOUND",
        "ticker": ticker, "applied_fields": [], "skipped_missing": [],
        "conflicts": [],
        "warnings": [f"SEC_UPDATES_NOT_FOUND: no {ticker}_sec_payload_updates.json under {sec_dir}"],
    }
