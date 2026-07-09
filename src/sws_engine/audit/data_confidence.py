"""Data Confidence v1.1 for the Personal Investment Research Audit Engine.

P0.2 scope: strengthen the P0.1 confidence layer with explicit audit policies,
field-level lineage inspection, source-registry tiers, and stale-field detection.
It remains an auxiliary audit result. It never normalizes scores, never hides
UNKNOWN checks, and never fabricates missing inputs.
"""
from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Dict, Mapping

from sws_engine.audit.missing_inputs import classify_missing_inputs, unknown_clusters
from sws_engine.audit.policies import (
    age_days,
    load_audit_policies,
    load_source_registry,
    source_registry_index,
    source_tier_for,
    ttl_for_tier,
)

QUALITY_WEIGHTS = {
    "exact": 1.0,
    "exact_or_approximation": 0.85,
    "approximation": 0.60,
    "approximation_or_missing": 0.40,
    "assumption": 0.30,
    "missing": 0.0,
}

GRADE_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "UNKNOWN": 0}


def _policies(audit_policies: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return audit_policies or load_audit_policies()


def _registry(source_registry: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return source_registry or load_source_registry()


def _dc_policy(audit_policies: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return (_policies(audit_policies).get("data_confidence") or {})


def _score_quality(value: str | None, audit_policies: Mapping[str, Any] | None = None) -> float:
    weights = (_dc_policy(audit_policies).get("source_quality_weights") or QUALITY_WEIGHTS)
    return float(weights.get(str(value or "missing"), 0.0))


def _coverage_values(output: Dict[str, Any]) -> list[float]:
    values: list[float] = []
    for score in (output.get("scores") or {}).values():
        try:
            values.append(float(score.get("coverage_pct", 0.0)))
        except (TypeError, ValueError):
            values.append(0.0)
    return values


def _confidence_grade(score: float, audit_policies: Mapping[str, Any] | None = None) -> str:
    thresholds = (_dc_policy(audit_policies).get("grade_thresholds") or {"A": 0.85, "B": 0.70, "C": 0.50, "D": 0.30})
    if score >= float(thresholds.get("A", 0.85)):
        return "A"
    if score >= float(thresholds.get("B", 0.70)):
        return "B"
    if score >= float(thresholds.get("C", 0.50)):
        return "C"
    if score >= float(thresholds.get("D", 0.30)):
        return "D"
    return "E"


def _grade_level(grade: str, audit_policies: Mapping[str, Any] | None = None) -> str:
    level_map = (_dc_policy(audit_policies).get("level_map") or {"A": "HIGH", "B": "HIGH", "C": "MEDIUM", "D": "LOW", "E": "LOW"})
    return str(level_map.get(grade, "UNKNOWN"))


def _cap_for_provider(grade: str, output: Dict[str, Any], audit_policies: Mapping[str, Any] | None = None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    provider = output.get("provider_profile")
    caps = (_dc_policy(audit_policies).get("provider_caps") or {})
    cap = caps.get(provider) or {}
    max_grade = cap.get("max_grade")
    if max_grade and GRADE_ORDER.get(grade, 0) > GRADE_ORDER.get(str(max_grade), 0):
        code = cap.get("reason_code") or f"{provider}_CONFIDENCE_CAP"
        warnings.append(f"{code}: data confidence capped at grade {max_grade} because provider_profile={provider} is not official/curated.")
        return str(max_grade), warnings
    return grade, warnings


def assess_data_confidence(
    output: Dict[str, Any],
    *,
    input_payload: Dict[str, Any] | None = None,
    audit_policies: Mapping[str, Any] | None = None,
    source_registry: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    policies = _policies(audit_policies)
    registry = _registry(source_registry)
    checks = list(output.get("checks") or [])
    field_lineage = _field_lineage(output, input_payload)
    field_quality = _field_quality_details(field_lineage, policies, registry)
    if not checks:
        return {
            "status": "UNKNOWN",
            "level": "UNKNOWN",
            "confidence_grade": "UNKNOWN",
            "reason_codes": ["NO_CHECKS_AVAILABLE"],
            "coverage_pct_overall": None,
            "unknown_checks_count": 0,
            "warnings_count": len(output.get("warnings") or []),
            "source_quality_mix": {},
            "source_class_mix": {},
            "source_tier_mix": field_quality["source_tier_mix"],
            "critical_missing_inputs": [],
            "unknown_clusters": [],
            "provider_degradation_visible": output.get("provider_profile") == "yfinance_pragmatic",
            "field_quality_details": field_quality["fields"],
            "stale_fields": field_quality["stale_fields"],
            "field_lineage_score": field_quality["field_lineage_score"],
            "input_lineage_summary": _lineage_summary(output, input_payload),
            "policy_version": _policy_version(policies),
        }

    coverage_values = _coverage_values(output)
    coverage = mean(coverage_values) if coverage_values else 0.0
    unknown_count = sum(1 for ch in checks if ch.get("result") == "UNKNOWN")
    unknown_ratio = unknown_count / len(checks)
    quality_values = [_score_quality(ch.get("source_quality"), policies) for ch in checks]
    quality_score = mean(quality_values) if quality_values else 0.0
    field_lineage_score = float(field_quality["field_lineage_score"])
    weights = _normalized_weights((_dc_policy(policies).get("weights") or {}))
    raw_score = (
        coverage * weights.get("coverage_pct", 0.40)
        + quality_score * weights.get("source_quality", 0.30)
        + (1.0 - unknown_ratio) * weights.get("unknown_preservation", 0.20)
        + field_lineage_score * weights.get("field_lineage", 0.10)
    )
    grade = _confidence_grade(raw_score, policies)
    grade, cap_warnings = _cap_for_provider(grade, output, policies)
    level = _grade_level(grade, policies)
    reason_codes: list[str] = []
    if unknown_count:
        reason_codes.append("UNKNOWN_CHECKS_PRESENT")
    if output.get("provider_profile") == "yfinance_pragmatic":
        reason_codes.append("YFINANCE_PRAGMATIC_DEGRADED")
    if quality_score < 0.5:
        reason_codes.append("LOW_SOURCE_QUALITY_MIX")
    if coverage < 0.5:
        reason_codes.append("LOW_COVERAGE")
    if field_lineage_score < 0.5:
        reason_codes.append("LOW_FIELD_LINEAGE_COVERAGE")
    if field_quality["stale_fields"]:
        reason_codes.append("STALE_FIELDS_PRESENT")
    if not reason_codes:
        reason_codes.append("DATA_CONFIDENCE_SUFFICIENT")

    source_quality_mix = dict(sorted(Counter(str(ch.get("source_quality", "UNKNOWN")) for ch in checks).items()))
    source_class_mix = dict(sorted(Counter(str(ch.get("source_class", "UNKNOWN")) for ch in checks).items()))
    provider_degradation = output.get("provider_profile") == "yfinance_pragmatic" or any(
        "YFINANCE" in str(w).upper() or "PROVIDER" in str(w).upper()
        for w in (output.get("warnings") or [])
    )
    warnings = list(output.get("warnings") or []) + cap_warnings
    return {
        "status": "PASS",
        "level": level,
        "confidence_grade": grade,
        "confidence_score": round(raw_score, 4),
        "coverage_pct_overall": round(coverage, 4),
        "unknown_checks_count": unknown_count,
        "unknown_checks_ratio": round(unknown_ratio, 4),
        "warnings_count": len(warnings),
        "source_quality_score": round(quality_score, 4),
        "source_quality_mix": source_quality_mix,
        "source_class_mix": source_class_mix,
        "source_tier_mix": field_quality["source_tier_mix"],
        "critical_missing_inputs": classify_missing_inputs(checks, input_payload=input_payload),
        "unknown_clusters": unknown_clusters(checks),
        "provider_degradation_visible": provider_degradation,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "field_quality_details": field_quality["fields"],
        "stale_fields": field_quality["stale_fields"],
        "field_lineage_score": round(field_lineage_score, 4),
        "policy_version": _policy_version(policies),
        "input_lineage_summary": _lineage_summary(output, input_payload),
    }


def _normalized_weights(weights: Mapping[str, Any]) -> dict[str, float]:
    defaults = {"coverage_pct": 0.40, "source_quality": 0.30, "unknown_preservation": 0.20, "field_lineage": 0.10}
    merged = {k: float(weights.get(k, v)) for k, v in defaults.items()}
    total = sum(merged.values()) or 1.0
    return {k: v / total for k, v in merged.items()}


def _policy_version(policies: Mapping[str, Any]) -> str | None:
    return ((policies.get("metadata") or {}).get("version"))


def _field_lineage(output: Dict[str, Any], input_payload: Dict[str, Any] | None) -> Dict[str, Any]:
    lineage = output.get("lineage") or {}
    payload_lineage = (input_payload or {}).get("lineage") or {}
    field_lineage = payload_lineage.get("field_lineage") or lineage.get("field_lineage") or {}
    return field_lineage if isinstance(field_lineage, dict) else {}


def _field_quality_details(field_lineage: Mapping[str, Any], policies: Mapping[str, Any], registry: Mapping[str, Any]) -> Dict[str, Any]:
    registry_by_id = source_registry_index(registry)
    source_tier_counts: Counter[str] = Counter()
    fields: list[dict[str, Any]] = []
    stale_fields: list[dict[str, Any]] = []
    if not field_lineage:
        return {"fields": [], "stale_fields": [], "source_tier_mix": {}, "field_lineage_score": 0.0}
    scores: list[float] = []
    for field, raw_info in sorted(field_lineage.items()):
        info = raw_info if isinstance(raw_info, dict) else {"source_id": str(raw_info)}
        source_id = info.get("source_id") or info.get("source") or info.get("provider")
        tier = info.get("tier") or source_tier_for(str(source_id) if source_id else None, registry)
        source_tier_counts[str(tier)] += 1
        quality = info.get("source_quality") or info.get("quality") or registry_by_id.get(str(source_id), {}).get("source_quality_default") or "missing"
        q_score = _score_quality(str(quality), policies)
        ttl = ttl_for_tier(str(tier), policies)
        as_of = info.get("as_of") or info.get("date") or info.get("fetched_at")
        age = age_days(as_of)
        stale = bool(ttl is not None and age is not None and age > ttl)
        if stale:
            q_score *= 0.5
        rec = {
            "field": str(field),
            "source_id": source_id,
            "source_tier": str(tier),
            "source_quality": str(quality),
            "as_of": as_of,
            "age_days": age,
            "ttl_days": ttl,
            "stale": stale,
            "score": round(q_score, 4),
        }
        fields.append(rec)
        scores.append(q_score)
        if stale:
            stale_fields.append(rec)
    return {
        "fields": fields,
        "stale_fields": stale_fields,
        "source_tier_mix": dict(sorted(source_tier_counts.items())),
        "field_lineage_score": mean(scores) if scores else 0.0,
    }


def _lineage_summary(output: Dict[str, Any], input_payload: Dict[str, Any] | None) -> Dict[str, Any]:
    lineage = output.get("lineage") or {}
    field_lineage = _field_lineage(output, input_payload)
    return {
        "provider_profile": output.get("provider_profile") or (input_payload or {}).get("provider_profile"),
        "output_lineage_keys": sorted(lineage.keys()),
        "field_lineage_count": len(field_lineage),
        "has_assumptions_hash": bool(lineage.get("assumptions_hash") or output.get("assumptions_hash")),
    }
