"""Legal/use-scope gate for the SWS Snowflake Engine implementation.

This module does not provide legal advice. It enforces an operational guardrail:
internal non-commercial use can proceed with attribution/disclaimer controls;
external/commercial use is blocked unless the user records a legal review.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

INTERNAL_SCOPES = {
    "internal_personal_educational",
    "internal_non_commercial_prototype",
}


@dataclass
class LegalScopeReport:
    status: str
    usage_scope: str | None
    commercial_use_enabled: bool
    external_access_enabled: bool
    legal_review_completed: bool
    blocking_issues: list[str]
    warnings: list[str]
    path: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "usage_scope": self.usage_scope,
            "commercial_use_enabled": self.commercial_use_enabled,
            "external_access_enabled": self.external_access_enabled,
            "legal_review_completed": self.legal_review_completed,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "path": self.path,
            "note": "This is an operational use-scope gate, not legal advice.",
        }


def load_legal_scope(path: str | Path = "config/legal_scope.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {
            "usage_scope": None,
            "commercial_use_enabled": False,
            "external_access_enabled": False,
            "legal_review_completed": False,
            "_missing_file": str(path),
        }
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def validate_legal_scope(path: str | Path = "config/legal_scope.yaml") -> LegalScopeReport:
    data = load_legal_scope(path)
    issues: list[str] = []
    warnings: list[str] = []
    usage_scope = data.get("usage_scope")
    commercial = bool(data.get("commercial_use_enabled"))
    external = bool(data.get("external_access_enabled"))
    reviewed = bool(data.get("legal_review_completed"))

    if data.get("_missing_file"):
        issues.append(f"legal scope file missing: {data['_missing_file']}")
    if not usage_scope:
        issues.append("usage_scope is not set")
    elif usage_scope not in INTERNAL_SCOPES and not reviewed:
        issues.append(f"usage_scope={usage_scope!r} requires legal_review_completed=true")
    if commercial and not reviewed:
        issues.append("commercial_use_enabled=true requires legal_review_completed=true")
    if external and not reviewed:
        issues.append("external_access_enabled=true requires legal_review_completed=true")

    constraints = data.get("license_constraints_acknowledged") or {}
    for key in (
        "attribution_required",
        "non_commercial_required_without_separate_review",
        "share_alike_notice_required_for_published_derivatives",
        "not_investment_advice_required",
    ):
        if constraints.get(key) is not True:
            warnings.append(f"license constraint not acknowledged: {key}")

    if usage_scope in INTERNAL_SCOPES and not commercial and not external:
        warnings.append("scope is internal/non-commercial; external or commercial deployment remains blocked without review")

    status = "PASS" if not issues else "FAIL"
    return LegalScopeReport(
        status=status,
        usage_scope=usage_scope,
        commercial_use_enabled=commercial,
        external_access_enabled=external,
        legal_review_completed=reviewed,
        blocking_issues=issues,
        warnings=warnings,
        path=str(path),
    )
