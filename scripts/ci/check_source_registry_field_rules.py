#!/usr/bin/env python
"""Validate v4.0 P0.2 source-registry audit metadata.

This gate is intentionally structural. It does not claim production readiness;
it checks that every registered source has audit-layer metadata needed by Data
Confidence and Model Applicability.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sws_engine.audit.policies import load_source_registry  # noqa: E402

REQUIRED_SOURCE_KEYS = {"tier", "license_status", "ttl_days"}
VALID_TIERS = {"official_filing", "curated", "pragmatic", "manual", "synthetic"}


def main() -> int:
    registry = load_source_registry(ROOT / "config/source_registry.yaml")
    errors: list[str] = []
    for src in registry.get("sources", []) or []:
        sid = src.get("id") or "<missing-id>"
        missing = sorted(k for k in REQUIRED_SOURCE_KEYS if k not in src)
        if missing:
            errors.append(f"{sid}: missing source audit metadata: {', '.join(missing)}")
        tier = src.get("tier")
        if tier and tier not in VALID_TIERS:
            errors.append(f"{sid}: invalid tier {tier!r}; expected one of {sorted(VALID_TIERS)}")
        if "yfinance" in str(src.get("provider", "")).lower() and tier == "official_filing":
            errors.append(f"{sid}: yfinance must not be registered as official_filing")
    field_rules = registry.get("field_rules") or {}
    if not field_rules:
        errors.append("field_rules: missing v4.0 field-level source rules")
    for field, rule in field_rules.items():
        if not rule.get("allowed_sources"):
            errors.append(f"field_rules.{field}: allowed_sources is required")
        if not rule.get("conflict_policy"):
            errors.append(f"field_rules.{field}: conflict_policy is required")
    if errors:
        print("SOURCE_REGISTRY_FIELD_RULES_FAIL")
        for err in errors:
            print(f"- {err}")
        return 1
    print("SOURCE_REGISTRY_FIELD_RULES_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
