"""Reason-code dictionary loader and completeness validation.

P0.6 scope: deterministic templates only. The dictionary does not call an LLM
and does not introduce facts beyond check/audit/sensitivity artifacts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

from sws_engine.core.enums import ReasonCode

DEFAULT_REASON_CODE_DICTIONARY = "config/reason_code_dictionary.yaml"

# Reason codes emitted by v4 audit/sources/sensitivity slices that are not part
# of the closed v3.1 CheckResult enum. Keeping this explicit avoids scanning
# arbitrary strings at runtime and makes the governance gate deterministic.
REQUIRED_AUXILIARY_REASON_CODES = {
    "MISSING_FCF_ESTIMATES",
    "MISSING_RISK_FREE_RATE_AND_EQUITY_RISK_PREMIUM",
    "NO_CHECKS_AVAILABLE",
    "UNKNOWN_CHECKS_PRESENT",
    "YFINANCE_PRAGMATIC_DEGRADED",
    "YFINANCE_PRAGMATIC_CONFIDENCE_CAP",
    "LOW_SOURCE_QUALITY_MIX",
    "LOW_COVERAGE",
    "LOW_FIELD_LINEAGE_COVERAGE",
    "STALE_FIELDS_PRESENT",
    "DATA_CONFIDENCE_SUFFICIENT",
    "DATA_CONFIDENCE_UNAVAILABLE",
    "LOW_DATA_CONFIDENCE",
    "MEDIUM_DATA_CONFIDENCE",
    "DATA_CONFIDENCE_UNKNOWN",
    "MANY_UNKNOWN_CHECKS",
    "PROVIDER_DEGRADATION_VISIBLE",
    "MODEL_APPLICABILITY_UNAVAILABLE",
    "MODEL_NOT_APPLICABLE",
    "MODEL_APPLICABILITY_UNKNOWN",
    "SCORE_USAGE_RESTRICTED",
    "CONCLUSION_RISK_LOW_BY_AUDIT_RULES",
    "STANDARD_EQUITY_MODEL_APPLICABLE",
    "BANK_STANDARD_FCF_MODEL_LIMITED",
    "REIT_REQUIRES_AFFO_FFO_NAV",
    "FUND_NOT_COMPANY_ANALYSIS_TARGET",
    "INSURANCE_REQUIRES_CONTEXTUAL_INTERPRETATION",
    "UTILITY_REQUIRES_CONTEXTUAL_INTERPRETATION",
    "COMMODITY_CYCLICAL_REQUIRES_CONTEXTUAL_INTERPRETATION",
    "PHARMA_REQUIRES_CONTEXTUAL_INTERPRETATION",
    "ADR_FOREIGN_REQUIRES_CONTEXTUAL_INTERPRETATION",
    "LOSS_MAKING_REQUIRES_CONTEXTUAL_INTERPRETATION",
    "XBRL_TAG_MISSING",
    "CIK_NOT_FOUND",
    "INVALID_RATE_VALUE",
    "MISSING_DATE_OR_RATE",
    "SENSITIVITY_COMPUTED",
    "SENSITIVITY_UNAVAILABLE",
    "SENSITIVITY_UNAVAILABLE_FOR_MANUAL_FAIR_VALUE",
    "VALUATION_DETAILS_UNAVAILABLE",
    "TERMINAL_VALUE_INPUTS_MISSING",
    "TERMINAL_VALUE_COMPUTED",
    "INSUFFICIENT_SENSITIVITY_VALUES",
    "FRAGILITY_COMPUTED",
    "REVERSE_DCF_ANALYST_FCF_NOT_IMPLEMENTED",
    "REVERSE_DCF_INPUTS_MISSING",
    "DISCOUNT_RATE_NOT_ABOVE_TERMINAL_GROWTH",
    "REVERSE_DCF_PRICE_OUTSIDE_BRACKET",
    "REVERSE_DCF_IMPLIED_GROWTH_COMPUTED",
    "SCENARIO_COMPUTED",
    "SCENARIO_VALUATION_UNKNOWN",
    "BUSINESS_RISK_SIGNALS_COMPUTED",
    "BUSINESS_RISK_INPUTS_MISSING",
    "RED_FLAG_NEGATIVE_OPERATING_CASH_FLOW",
    "RED_FLAG_NEGATIVE_FREE_CASH_FLOW",
    "RED_FLAG_EARNINGS_CASH_FLOW_DIVERGENCE",
    "RED_FLAG_DIVIDEND_NOT_COVERED_BY_FCF",
    "RED_FLAG_HIGH_INTANGIBLES_TO_ASSETS",
    "RED_FLAG_ELEVATED_NET_DEBT_TO_EQUITY",
    "RED_FLAG_SHARE_DILUTION_ABOVE_10PCT",
    "RED_FLAG_ENGINE_UNKNOWN_CHECKS_PRESENT",
    "ACCOUNTING_QUALITY_ACCRUALS_RATIO",
    "ACCOUNTING_QUALITY_FCF_CONVERSION",
    "ACCOUNTING_QUALITY_MARGIN_VARIABILITY",
    "ACCOUNTING_QUALITY_WEAK",
    "ACCOUNTING_QUALITY_WATCH",
    "ACCOUNTING_QUALITY_NORMAL",
    "CAPITAL_ALLOCATION_DIVIDENDS_TO_FCF",
    "CAPITAL_ALLOCATION_BUYBACKS_TO_FCF",
    "CAPITAL_ALLOCATION_CAPEX_INTENSITY",
    "CAPITAL_ALLOCATION_SHARE_COUNT_GROWTH",
    "CAPITAL_ALLOCATION_WATCH",
    "CAPITAL_ALLOCATION_BALANCED",
    "WATCHLIST_AUDIT_COMPUTED",
    "WATCHLIST_INPUTS_MISSING",
    "WATCHLIST_AUDIT_ARTIFACTS_MISSING",
    "WATCHLIST_AUDIT_ARTIFACT_MISSING",
    "WATCHLIST_TICKER_MISSING",
    "WATCHLIST_RESEARCHABLE_NOW",
    "WATCHLIST_DATA_LIMITED",
    "WATCHLIST_NEEDS_DIFFERENT_MODEL",
    "WATCHLIST_NOT_APPLICABLE_IGNORED",
    "WATCHLIST_MODEL_APPLICABILITY_UNKNOWN",
    "WATCHLIST_CONCLUSION_RISK_REVIEW_REQUIRED",
    "WATCHLIST_RED_FLAGS_REVIEW_REQUIRED",
    "WATCHLIST_PROVIDER_DEGRADED",
    "THESIS_INPUTS_MISSING",
    "THESIS_NO_EVALUABLE_RULES",
    "THESIS_INVALIDATION_TRIGGERED",
    "THESIS_MAJORITY_RULES_UNKNOWN",
    "THESIS_WATCH_METRIC_TRIGGERED",
    "THESIS_RULES_PARTIALLY_UNKNOWN",
    "THESIS_ON_TRACK",
    "THESIS_RULE_INPUT_MISSING",
    "THESIS_RULE_COMPARISON_FAILED",
    "THESIS_RULE_TRIGGERED",
    "THESIS_RULE_OK",
    "DECISION_RECORDED",
    "DECISION_INPUTS_MISSING",
    "DECISION_TYPE_NOT_ALLOWED",
    "PORTFOLIO_INPUTS_MISSING",
    "PORTFOLIO_AUDIT_ARTIFACTS_MISSING",
    "PORTFOLIO_AUDIT_COMPUTED",
    "PORTFOLIO_WEIGHTED_DATA_CONFIDENCE_COMPUTED",
    "PORTFOLIO_WEIGHTED_CONCLUSION_RISK_COMPUTED",
    "PORTFOLIO_UNKNOWN_EXPOSURE_PRESENT",
    "PORTFOLIO_NO_UNKNOWN_EXPOSURE",
    "PORTFOLIO_PROVIDER_DEGRADATION_EXPOSURE",
    "PORTFOLIO_NO_PROVIDER_DEGRADATION_EXPOSURE",
    "PORTFOLIO_CONCENTRATION_COMPUTED",
    "PORTFOLIO_CONCENTRATION_HIGH",
    "PORTFOLIO_MACRO_EXPOSURE_COMPUTED",
    "PORTFOLIO_MACRO_EXPOSURE_UNKNOWN",
    "PORTFOLIO_ATTRIBUTION_LITE_COMPUTED",
    "PORTFOLIO_ATTRIBUTION_INPUTS_MISSING",
    "PORTFOLIO_COMPONENT_UNKNOWN",
    "MEMO_INPUTS_MISSING",
    "MEMO_GENERATED",
    "MEMO_COMPONENT_UNKNOWN",
    "MEMO_UNKNOWN_PRESERVED",
    "MEMO_FALSE_PRECISION_GUARDRAIL_APPLIED",
    "MEMO_RECOMMENDATION_LANGUAGE_REJECTED",
    "MEMO_NO_RECOMMENDATION_LANGUAGE",
    "MEMO_MANUAL_REVIEW_REQUIRED",
    "RUN_COMPARISON_INPUTS_MISSING",
    "RUN_COMPARISON_COMPUTED",
    "RUN_COMPARISON_CHANGES_DETECTED",
    "RUN_COMPARISON_NO_MATERIAL_CHANGE",
    "RUN_COMPARISON_UNKNOWN_PRESERVED",
    "RUN_COMPARISON_NO_UNKNOWN_DETECTED",
    "RUN_COMPARISON_CHECKS_CHANGED",
    "RUN_COMPARISON_CHECKS_UNCHANGED_OR_UNAVAILABLE",
    "RUN_COMPARISON_LINEAGE_CHANGED",
    "RUN_COMPARISON_LINEAGE_UNCHANGED_OR_UNAVAILABLE",
    "RUN_COMPARISON_NO_RECOMMENDATION_LANGUAGE",
    "RUN_COMPARISON_RECOMMENDATION_LANGUAGE_REJECTED",
    "WORKFLOW_PACKAGE_INPUTS_MISSING",
    "WORKFLOW_PACKAGE_READY",
    "WORKFLOW_COMPONENT_READY",
    "WORKFLOW_OPTIONAL_COMPONENT_MISSING",
    "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED",
    "WORKFLOW_PACKAGE_MANUAL_REVIEW_REQUIRED",
    "WORKFLOW_DASHBOARD_API_ONLY",
    "WORKFLOW_NO_RECOMMENDATION_LANGUAGE",
    "WORKFLOW_RECOMMENDATION_LANGUAGE_REJECTED",
    "RELEASE_MVP_COMPLETE",
    "RELEASE_MVP_COMPLETE_WITH_LIMITATIONS",
    "RELEASE_REQUIRED_ARTIFACT_MISSING",
    "RELEASE_CAPABILITY_PRESENT",
    "RELEASE_CAPABILITY_ARTIFACT_MISSING",
    "RELEASE_PRODUCTION_NOT_READY",
    "RELEASE_OPTIONAL_ARTIFACT_MISSING",
    "RELEASE_GATES_NOT_RUN",
    "RELEASE_GUARDRAILS_PASS",
    "RELEASE_LOCAL_SMOKE_COMPLETED",
}

REQUIRED_REASON_CODES = {code.value for code in ReasonCode} | REQUIRED_AUXILIARY_REASON_CODES


def load_reason_code_dictionary(path: str | Path | None = None) -> Dict[str, Any]:
    p = Path(path or DEFAULT_REASON_CODE_DICTIONARY)
    if not p.exists():
        raise FileNotFoundError(f"Reason-code dictionary not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("reason_codes", {})
    data.setdefault("defaults", {})
    return data


def get_reason_template(dictionary: Mapping[str, Any], reason_code: str) -> Dict[str, Any]:
    entries = dictionary.get("reason_codes") or {}
    defaults = dictionary.get("defaults") or {}
    entry = entries.get(reason_code) or {}
    return {
        "severity": entry.get("severity") or defaults.get("severity") or "INFO",
        "analyst": entry.get("analyst") or defaults.get("analyst") or "Reason `{reason_code}` was emitted.",
        "plain_english": entry.get("plain_english") or defaults.get("plain_english") or "The engine emitted this reason code.",
        "remediation_hint": entry.get("remediation_hint") or defaults.get("remediation_hint") or "Review the cited data and lineage.",
        "known_reason_code": reason_code in entries,
    }


def validate_reason_code_dictionary(path: str | Path | None = None, *, required_codes: set[str] | None = None) -> Dict[str, Any]:
    dictionary = load_reason_code_dictionary(path)
    entries = set((dictionary.get("reason_codes") or {}).keys())
    required = set(required_codes or REQUIRED_REASON_CODES)
    missing = sorted(required - entries)
    empty_templates: list[str] = []
    for code in sorted(entries & required):
        tmpl = get_reason_template(dictionary, code)
        if not str(tmpl.get("analyst") or "").strip() or not str(tmpl.get("plain_english") or "").strip():
            empty_templates.append(code)
    return {
        "status": "PASS" if not missing and not empty_templates else "FAIL",
        "dictionary_path": str(path or DEFAULT_REASON_CODE_DICTIONARY),
        "metadata": dictionary.get("metadata") or {},
        "required_count": len(required),
        "entries_count": len(entries),
        "missing_reason_codes": missing,
        "empty_templates": empty_templates,
        "not_investment_advice": bool((dictionary.get("metadata") or {}).get("not_investment_advice")),
    }
