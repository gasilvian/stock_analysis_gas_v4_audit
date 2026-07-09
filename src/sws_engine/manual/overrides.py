"""Manual override workflow (Plan B).

This module makes the manual-input path explicit instead of allowing silent
fallbacks. Overrides are small JSON files with either:

    {"fields": {"field_name": {"value": ..., "source_quality": "exact", "source_class": "E3"}}}

or a plain {"field_name": value} dict. The merge keeps lineage visible so
outputs remain auditable under the v3.1 data contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sws_engine.providers.provider_lineage import attach_field_lineage, field_meta
from sws_engine.core.enums import SourceClass, SourceQuality
from sws_engine.providers.capability_matrix import YFINANCE_CAPABILITY


CHECK_FIELD_MAP: dict[str, list[str]] = {
    "V1": ["price", "fair_value"],
    "V2": ["price", "fair_value"],
    "V3": ["price", "eps", "market_averages"],
    "V4": ["price", "eps", "industry_averages"],
    "V5": ["price", "eps", "earnings_growth"],
    "V6": ["price", "total_assets", "intangible_assets", "total_liabilities", "shares_outstanding", "industry_averages"],
    "F1": ["earnings_growth", "market_averages"],
    "F2": ["earnings_growth", "market_averages"],
    "F3": ["revenue_growth", "market_averages"],
    "F4": ["earnings_growth"],
    "F5": ["revenue_growth"],
    "F6": ["roe_3y_estimate"],
    "P1": ["eps_growth_1y", "industry_averages"],
    "P2": ["current_eps", "eps_5y_ago"],
    "P3": ["eps_growth_1y", "eps_growth_5y_avg"],
    "P4": ["roe", "equity"],
    "P5": ["roce_current", "roce_3y_ago"],
    "P6": ["roa", "industry_averages"],
    "H1": ["st_assets", "st_liabilities"],
    "H2": ["st_assets", "lt_liabilities"],
    "H3": ["debt_to_equity_current", "debt_to_equity_5y_ago", "equity"],
    "H4": ["debt_to_equity_current", "equity"],
    "H5": ["operating_cash_flow", "total_debt"],
    "H6": ["ebit", "net_interest_expense", "total_debt"],
    "D1": ["dividend_yield", "market_averages"],
    "D2": ["dividend_yield", "market_averages"],
    "D3": ["dps_history_10y"],
    "D4": ["dps_history_10y"],
    "D5": ["payout_ratio"],
    "D6": ["estimated_payout_3y"],
}

RECOMMENDED_OVERRIDE_TEMPLATES = {
    "analyst_estimates_weighted": "templates/manual_override_template.json",
    "fcf_estimates": "templates/manual_override_template.json",
    "market_averages": "templates/manual_override_template.json",
    "industry_averages": "templates/manual_override_template.json",
    "risk_free_rate_10y_5y_avg": "templates/manual_override_template.json",
    "equity_risk_premium": "templates/manual_override_template.json",
    "affo_ffo_nav": "templates/reit_manual_override_template.json",
    "estimated_payout_3y": "templates/reit_manual_override_template.json",
    "bank_deposits_npl_chargeoffs": "templates/bank_manual_override_template.json",
    "deposits": "templates/bank_manual_override_template.json",
    "npl": "templates/bank_manual_override_template.json",
    "allowance_for_npl": "templates/bank_manual_override_template.json",
    "net_charge_offs": "templates/bank_manual_override_template.json",
}


@dataclass
class OverrideMergeReport:
    applied_fields: list[str]
    warnings: list[str]
    output_path: str | None = None


def load_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_override_file(path: str | Path) -> dict:
    obj = load_json(path)
    if not isinstance(obj, dict):
        raise ValueError(f"override file must be a JSON object: {path}")
    return obj


def _normalize_override(obj: dict) -> dict[str, dict[str, Any]]:
    fields = obj.get("fields", obj)
    if not isinstance(fields, dict):
        raise ValueError("override 'fields' must be an object")
    out: dict[str, dict[str, Any]] = {}
    for name, spec in fields.items():
        if isinstance(spec, dict) and "value" in spec:
            out[name] = {
                "value": spec.get("value"),
                "source_quality": spec.get("source_quality", SourceQuality.EXACT.value),
                "source_class": spec.get("source_class", SourceClass.E3.value),
                "source": spec.get("source", "manual_override"),
                "as_of": spec.get("as_of"),
                "note": spec.get("note"),
            }
        else:
            out[name] = {
                "value": spec,
                "source_quality": SourceQuality.EXACT.value,
                "source_class": SourceClass.E3.value,
                "source": "manual_override",
                "as_of": None,
                "note": None,
            }
    return out


def merge_overrides(base_payload: dict, override_specs: list[dict]) -> tuple[dict, OverrideMergeReport]:
    """Return a new payload with manual override fields applied and lineaged."""
    payload = json.loads(json.dumps(base_payload))
    payload.setdefault("lineage", {}).setdefault("field_lineage", {})
    payload.setdefault("builder_warnings", [])
    applied: list[str] = []
    warnings: list[str] = []
    for obj in override_specs:
        for field, spec in _normalize_override(obj).items():
            payload[field] = spec["value"]
            attach_field_lineage(payload, field, field_meta(
                provider=spec.get("source") or "manual_override",
                source_field=field,
                source_quality=spec["source_quality"],
                source_class=spec["source_class"],
                as_of=spec.get("as_of"),
                transform="manual_override_merge",
            ))
            applied.append(field)
    if applied:
        warnings.append("MANUAL_OVERRIDE_USED: manual override fields applied; review source_quality/source_class before use")
        payload["builder_warnings"].extend(warnings)
    payload["builder_warnings"] = list(dict.fromkeys(payload.get("builder_warnings", [])))
    return payload, OverrideMergeReport(applied_fields=applied, warnings=warnings)


def missing_fields(payload: dict) -> list[str]:
    """Fields known to matter for provider capability that are absent/null."""
    fields = sorted(set(YFINANCE_CAPABILITY) - {"ticker", "exchange"})
    return [f for f in fields if payload.get(f) is None]


def impacted_checks_for_missing(missing: list[str]) -> dict[str, list[str]]:
    missing_set = set(missing)
    impacted: dict[str, list[str]] = {}
    for check, fields in CHECK_FIELD_MAP.items():
        hit = sorted(missing_set.intersection(fields))
        if hit:
            impacted[check] = hit
    return impacted


def override_recommendations(missing: list[str]) -> dict[str, str]:
    return {f: RECOMMENDED_OVERRIDE_TEMPLATES.get(f, "templates/company_input_template.json") for f in missing}


def dry_run_report(payload: dict) -> dict:
    missing = missing_fields(payload)
    return {
        "ticker": payload.get("ticker"),
        "provider_profile": payload.get("provider_profile"),
        "missing_fields": missing,
        "impacted_checks_likely_unknown": impacted_checks_for_missing(missing),
        "manual_override_recommendations": override_recommendations(missing),
        "note": "Dry-run only. Missing fields must remain UNKNOWN unless a documented fallback or explicit manual override is supplied.",
    }
