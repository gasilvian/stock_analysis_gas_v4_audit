"""Audit-layer policy and registry helpers.

These helpers are intentionally auxiliary: they never modify v3.1 checks,
valuation, growth, portfolio logic, or output_schema.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

DEFAULT_AUDIT_POLICIES_PATH = "config/audit_policies.yaml"
DEFAULT_SOURCE_REGISTRY_PATH = "config/source_registry.yaml"

DEFAULT_AUDIT_POLICIES: Dict[str, Any] = {
    "data_confidence": {
        "weights": {"coverage_pct": 0.40, "source_quality": 0.30, "unknown_preservation": 0.20, "field_lineage": 0.10},
        "grade_thresholds": {"A": 0.85, "B": 0.70, "C": 0.50, "D": 0.30},
        "level_map": {"A": "HIGH", "B": "HIGH", "C": "MEDIUM", "D": "LOW", "E": "LOW"},
        "source_quality_weights": {
            "exact": 1.0,
            "exact_or_approximation": 0.85,
            "approximation": 0.60,
            "approximation_or_missing": 0.40,
            "assumption": 0.30,
            "missing": 0.0,
        },
        "provider_caps": {"yfinance_pragmatic": {"max_grade": "C", "reason_code": "YFINANCE_PRAGMATIC_CONFIDENCE_CAP"}},
        "field_criticality_weights": {"unknown_input": 0.5},
        "ttl_days_by_tier": {"official_filing": 120, "curated": 45, "pragmatic": 7, "manual": 30, "synthetic": 0},
    },
    "model_applicability": {
        "default_unknown_usage": "audit_only",
        "allowed_score_usage": {},
        "reason_codes": {},
    },
}


def load_yaml_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def load_audit_policies(path: str | Path = DEFAULT_AUDIT_POLICIES_PATH) -> Dict[str, Any]:
    loaded = load_yaml_file(path)
    return _deep_merge(DEFAULT_AUDIT_POLICIES, loaded)


def load_source_registry(path: str | Path = DEFAULT_SOURCE_REGISTRY_PATH) -> Dict[str, Any]:
    return load_yaml_file(path)


def source_registry_index(registry: Mapping[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    return {str(s.get("id")): dict(s) for s in (registry or {}).get("sources", []) or [] if s.get("id")}


def field_rules_index(registry: Mapping[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    return {str(k): dict(v) for k, v in ((registry or {}).get("field_rules") or {}).items()}


def source_tier_for(source_id: str | None, registry: Mapping[str, Any] | None) -> str:
    if not source_id:
        return "unknown"
    entry = source_registry_index(registry).get(str(source_id), {})
    return str(entry.get("tier") or entry.get("source_tier") or entry.get("category") or "unknown")


def ttl_for_tier(tier: str, policies: Mapping[str, Any]) -> int | None:
    ttl = ((policies.get("data_confidence") or {}).get("ttl_days_by_tier") or {}).get(tier)
    try:
        return int(ttl)
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def age_days(as_of: Any, *, now: datetime | None = None) -> int | None:
    dt = parse_date(as_of)
    if not dt:
        return None
    current = now or datetime.now(timezone.utc)
    return max(0, (current - dt).days)


def _deep_merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for k, v in base.items():
        if isinstance(v, dict):
            result[k] = _deep_merge(v, {})
        else:
            result[k] = v
    for k, v in (override or {}).items():
        if isinstance(v, Mapping) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
