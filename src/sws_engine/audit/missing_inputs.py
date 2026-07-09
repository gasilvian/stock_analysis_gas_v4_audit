"""Critical missing-input classifier for the v4.0 audit layer.

This module is deliberately heuristic in P0.1: it only uses the published v3.1
output/check contract. It never invents input values and never converts UNKNOWN
checks into PASS/FAIL.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable

CRITICAL_FIELD_KEYWORDS: dict[str, list[str]] = {
    "fcf_estimates": ["fcf", "free_cash_flow", "free cash flow"],
    "risk_free_rate_10y_5y_avg": ["risk_free", "risk-free", "risk free", "discount_rate"],
    "equity_risk_premium": ["equity_risk_premium", "erp"],
    "analyst_estimates_weighted": ["analyst", "estimate", "forecast"],
    "bank_deposits_npl_chargeoffs": ["deposit", "npl", "chargeoff", "charge_off", "financial_h"],
    "affo_ffo_nav": ["affo", "ffo", "nav", "reit"],
    "market_averages": ["market_average", "market averages", "market_averages"],
    "industry_averages": ["industry_average", "industry averages", "industry_averages"],
    "intangible_assets": ["intangible", "goodwill", "tangible_book"],
    "operating_cash_flow": ["operating_cash_flow", "ocf", "cash flow"],
    "capex_history_3y": ["capex", "capital_expenditure"],
}

CRITICALITY_BY_FIELD: dict[str, str] = {
    "fcf_estimates": "critical",
    "risk_free_rate_10y_5y_avg": "critical",
    "equity_risk_premium": "critical",
    "analyst_estimates_weighted": "critical",
    "bank_deposits_npl_chargeoffs": "critical_for_banks",
    "affo_ffo_nav": "critical_for_reits",
    "market_averages": "important",
    "industry_averages": "important",
    "intangible_assets": "important",
    "operating_cash_flow": "important",
    "capex_history_3y": "important",
}


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{k} {_flatten_text(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(v) for v in value)
    return "" if value is None else str(value)


def infer_impacted_fields(check: Dict[str, Any]) -> list[str]:
    """Infer critical missing fields from a check without fabricating data."""
    haystack_parts = [
        str(check.get("reason_code", "")),
        str(check.get("name", "")),
        str(check.get("id", "")),
        _flatten_text(check.get("inputs", {})),
        _flatten_text(check.get("input_lineage", {})),
    ]
    haystack = " ".join(haystack_parts).lower()
    fields: list[str] = []
    for field, keywords in CRITICAL_FIELD_KEYWORDS.items():
        if field.lower() in haystack or any(k.lower() in haystack for k in keywords):
            fields.append(field)
    if not fields and (check.get("result") == "UNKNOWN" or check.get("source_quality") == "missing"):
        fields.append("unknown_input")
    return sorted(set(fields))


# P1.2-cal (B1): fields whose absence surfaces indirectly — a missing
# discount-rate input never appears by name in check text; it manifests as
# fair_value=None and value-axis UNKNOWN checks. When the payload proves the
# field is absent, these downstream keywords locate the affected checks so
# the ROOT CAUSE is reported instead of a coincidental keyword match.
DOWNSTREAM_KEYWORDS: dict[str, list[str]] = {
    "risk_free_rate_10y_5y_avg": ["fair_value"],
    "equity_risk_premium": ["fair_value"],
}


def _field_actually_present(field: str, input_payload: Dict[str, Any] | None) -> bool:
    """True when the payload demonstrably carries a non-null value for field.

    P1.2-cal (B1, second layer): missing-input classification is keyword
    inference over UNKNOWN checks and previously never consulted the payload,
    so a field could be reported as a critical missing input even when a
    curated value was present (observed in real calibration for
    risk_free_rate_10y_5y_avg). A field whose value exists and whose lineage
    is not marked missing must not be classified as missing. Payload absence
    of the key keeps the inference untouched — this only ever REMOVES false
    positives, never hides real gaps.
    """
    if not input_payload or field not in input_payload:
        return False
    if input_payload.get(field) is None:
        return False
    lineage = ((input_payload.get("lineage") or {}).get("field_lineage") or {})
    field_lineage = lineage.get(field) or {}
    if str(field_lineage.get("source_quality", "")).lower() == "missing":
        return False
    return True


def classify_missing_inputs(
    checks: Iterable[Dict[str, Any]],
    input_payload: Dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic critical-missing-input records for UNKNOWN checks."""
    by_field: dict[str, dict[str, Any]] = {}
    affected: dict[str, list[dict[str, str]]] = defaultdict(list)
    checks_list = list(checks)
    for check in checks_list:
        if check.get("result") != "UNKNOWN" and check.get("source_quality") != "missing":
            continue
        fields = infer_impacted_fields(check)
        for field in fields:
            if field != "unknown_input" and _field_actually_present(field, input_payload):
                continue
            affected[field].append({
                "axis": str(check.get("axis", "UNKNOWN")),
                "check_id": str(check.get("id", "UNKNOWN")),
                "name": str(check.get("name", "UNKNOWN")),
                "reason_code": str(check.get("reason_code", "UNKNOWN")),
            })
    # Payload-driven root-cause detection (P1.2-cal B1): when the payload
    # proves a critical rate field is genuinely absent, attribute the
    # downstream fair-value UNKNOWN checks to it explicitly.
    if input_payload:
        for field, downstream in DOWNSTREAM_KEYWORDS.items():
            if field in affected or _field_actually_present(field, input_payload):
                continue
            hits = []
            for check in checks_list:
                if check.get("result") != "UNKNOWN":
                    continue
                haystack = " ".join([
                    str(check.get("reason_code", "")), str(check.get("name", "")),
                    _flatten_text(check.get("inputs", {})),
                ]).lower()
                if any(k in haystack for k in downstream):
                    hits.append({
                        "axis": str(check.get("axis", "UNKNOWN")),
                        "check_id": str(check.get("id", "UNKNOWN")),
                        "name": str(check.get("name", "UNKNOWN")),
                        "reason_code": str(check.get("reason_code", "UNKNOWN")),
                    })
            if hits:
                affected[field].extend(hits)
    for field, checks_for_field in sorted(affected.items()):
        by_field[field] = {
            "field": field,
            "criticality": CRITICALITY_BY_FIELD.get(field, "unknown"),
            "checks_affected_count": len(checks_for_field),
            "checks_affected": checks_for_field,
            "remediation_hint": _remediation_hint(field),
        }
    return list(by_field.values())


def _remediation_hint(field: str) -> str:
    hints = {
        "fcf_estimates": "Provide manual FCF estimates or accept valuation degradation/UNKNOWN.",
        "risk_free_rate_10y_5y_avg": "Populate curated 10Y bond yield source or rates CSV.",
        "equity_risk_premium": "Populate reviewed ERP curated assumption; keep sensitivity_required=true.",
        "analyst_estimates_weighted": "Provide manual analyst estimates or let growth route degrade to historical fallback.",
        "bank_deposits_npl_chargeoffs": "Use bank-specific official/manual fields; do not compare with standard FCF equities.",
        "affo_ffo_nav": "Provide REIT AFFO/FFO/NAV manual curated inputs or keep REIT audit_only.",
        "market_averages": "Populate curated market averages snapshot.",
        "industry_averages": "Populate curated industry averages snapshot.",
        "intangible_assets": "Prefer SEC official filing value; do not infer from book value.",
        "operating_cash_flow": "Provide official or curated cash-flow statement input.",
        "capex_history_3y": "Provide official or curated capital-expenditure history.",
        "unknown_input": "Inspect check input_lineage and source provider limitations.",
    }
    return hints.get(field, "Inspect lineage and provide a reviewed input source.")


def unknown_clusters(checks: Iterable[Dict[str, Any]]) -> list[dict[str, Any]]:
    """Group UNKNOWN checks by reason_code for UI/report readability."""
    clusters: dict[str, dict[str, Any]] = {}
    for check in checks:
        if check.get("result") != "UNKNOWN":
            continue
        code = str(check.get("reason_code", "UNKNOWN"))
        clusters.setdefault(code, {"reason_code": code, "count": 0, "checks": []})
        clusters[code]["count"] += 1
        clusters[code]["checks"].append({
            "axis": check.get("axis"),
            "check_id": str(check.get("id")),
            "name": check.get("name"),
            "source_quality": check.get("source_quality"),
            "source_class": check.get("source_class"),
        })
    return sorted(clusters.values(), key=lambda item: (-item["count"], item["reason_code"]))
