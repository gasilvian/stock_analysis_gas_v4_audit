"""Conclusion risk v1.

Conclusion risk is a deterministic audit warning, not a recommendation. It is
computed with max/guardrail logic so drivers remain visible.
"""
from __future__ import annotations

from typing import Any, Dict, List

RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNKNOWN": 3}


def _max_risk(a: str, b: str) -> str:
    return a if RISK_ORDER.get(a, 3) >= RISK_ORDER.get(b, 3) else b


def assess_conclusion_risk(
    output: Dict[str, Any],
    *,
    data_confidence: Dict[str, Any] | None = None,
    model_applicability: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    drivers: List[Dict[str, Any]] = []
    risk = "LOW"
    dc = data_confidence or {}
    ma = model_applicability or {}

    if not dc:
        risk = _max_risk(risk, "MEDIUM")
        drivers.append({"reason_code": "DATA_CONFIDENCE_UNAVAILABLE", "risk_impact": "MEDIUM"})
    else:
        level = dc.get("level")
        if level == "LOW":
            risk = _max_risk(risk, "HIGH")
            drivers.append({"reason_code": "LOW_DATA_CONFIDENCE", "risk_impact": "HIGH"})
        elif level == "MEDIUM":
            risk = _max_risk(risk, "MEDIUM")
            drivers.append({"reason_code": "MEDIUM_DATA_CONFIDENCE", "risk_impact": "MEDIUM"})
        elif level == "UNKNOWN":
            risk = _max_risk(risk, "HIGH")
            drivers.append({"reason_code": "DATA_CONFIDENCE_UNKNOWN", "risk_impact": "HIGH"})
        unknown_count = int(dc.get("unknown_checks_count") or 0)
        if unknown_count >= 10:
            risk = _max_risk(risk, "HIGH")
            drivers.append({"reason_code": "MANY_UNKNOWN_CHECKS", "risk_impact": "HIGH", "unknown_checks_count": unknown_count})
        elif unknown_count > 0:
            risk = _max_risk(risk, "MEDIUM")
            drivers.append({"reason_code": "UNKNOWN_CHECKS_PRESENT", "risk_impact": "MEDIUM", "unknown_checks_count": unknown_count})
        if dc.get("provider_degradation_visible"):
            risk = _max_risk(risk, "MEDIUM")
            drivers.append({"reason_code": "PROVIDER_DEGRADATION_VISIBLE", "risk_impact": "MEDIUM"})

    if not ma:
        risk = _max_risk(risk, "MEDIUM")
        drivers.append({"reason_code": "MODEL_APPLICABILITY_UNAVAILABLE", "risk_impact": "MEDIUM"})
    else:
        status = ma.get("status")
        if status == "NOT_APPLICABLE":
            risk = _max_risk(risk, "HIGH")
            drivers.append({"reason_code": "MODEL_NOT_APPLICABLE", "risk_impact": "HIGH"})
        elif status == "DEGRADED":
            risk = _max_risk(risk, "HIGH")
            drivers.append({"reason_code": ma.get("reason_code", "MODEL_DEGRADED"), "risk_impact": "HIGH"})
        elif status == "UNKNOWN":
            risk = _max_risk(risk, "HIGH")
            drivers.append({"reason_code": "MODEL_APPLICABILITY_UNKNOWN", "risk_impact": "HIGH"})
        if ma.get("allowed_score_usage") in {"audit_only", "do_not_compare"}:
            risk = _max_risk(risk, "HIGH")
            drivers.append({
                "reason_code": "SCORE_USAGE_RESTRICTED",
                "risk_impact": "HIGH",
                "allowed_score_usage": ma.get("allowed_score_usage"),
            })

    if not drivers:
        drivers.append({"reason_code": "CONCLUSION_RISK_LOW_BY_AUDIT_RULES", "risk_impact": "LOW"})
    manual_review_items = _manual_review_items(drivers, dc, ma)
    return {
        "status": "PASS",
        "risk_level": risk,
        "drivers": drivers,
        "manual_review_required": risk in {"MEDIUM", "HIGH", "UNKNOWN"},
        "manual_review_items": manual_review_items,
        "source_quality": "approximation",
        "source_class": "E3",
        "input_lineage": {
            "data_confidence_level": dc.get("level"),
            "model_applicability_status": ma.get("status"),
            "unknown_checks_count": dc.get("unknown_checks_count"),
            "provider_profile": output.get("provider_profile"),
        },
    }


def _manual_review_items(drivers: list[dict[str, Any]], dc: Dict[str, Any], ma: Dict[str, Any]) -> list[str]:
    items: list[str] = []
    for driver in drivers:
        code = str(driver.get("reason_code"))
        if code in {"LOW_DATA_CONFIDENCE", "MEDIUM_DATA_CONFIDENCE", "MANY_UNKNOWN_CHECKS", "UNKNOWN_CHECKS_PRESENT"}:
            items.append("Review UNKNOWN checks and critical missing inputs before interpreting the score.")
        elif "BANK" in code:
            items.append("Use bank-specific analysis or manually curate bank fields before ranking.")
        elif "REIT" in code:
            items.append("Provide AFFO/FFO/NAV inputs before relying on REIT valuation conclusions.")
        elif code in {"MODEL_NOT_APPLICABLE", "MODEL_APPLICABILITY_UNKNOWN", "SCORE_USAGE_RESTRICTED"}:
            items.append("Do not compare this score cross-sector until model applicability is resolved.")
        elif code == "PROVIDER_DEGRADATION_VISIBLE":
            items.append("Verify important fields against official/curated sources; provider is pragmatic.")
    for missing in dc.get("critical_missing_inputs") or []:
        field = missing.get("field")
        if field and field != "unknown_input":
            items.append(f"Resolve or explicitly accept missing input: {field}.")
    if ma.get("comparability_warning"):
        items.append(str(ma["comparability_warning"]))
    return sorted(set(items))
