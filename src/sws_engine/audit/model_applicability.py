"""Model Applicability Gate v1.1.

The gate labels whether the existing v3.1 result can be interpreted/ranked. It
never changes engine routing or original checks. P0.2 adds optional Identifier
Master support and stricter allowed_score_usage metadata.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from sws_engine.audit.identifier_master import find_identifier_record
from sws_engine.audit.policies import load_audit_policies

STANDARD_OK = "STANDARD_OK"
DEGRADED = "DEGRADED"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"

RANKABLE = "rankable"
DISPLAY_ONLY = "display_only"
AUDIT_ONLY = "audit_only"
DO_NOT_COMPARE = "do_not_compare"

RECOMMENDED_MODELS = {
    "standard_industrial": "two_stage_fcf_or_ddm_as_applicable",
    "bank": "excess_returns_or_dividend_based",
    "insurance": "insurance_specific_model_required",
    "reit": "affo_dcf_or_nav_model",
    "fund_etf_excluded": "portfolio_fund_analysis_not_company_snowflake",
    "utility": "sector_contextual_review",
    "commodity_cyclical": "sector_contextual_review",
    "saas": "standard_equity_with_sbc_and_growth_caveats",
    "pharma": "pipeline_and_rnd_contextual_review",
    "adr_foreign": "manual_filing_currency_review",
    "loss_making": "cash_runway_and_optional_recovery_model",
    "unknown": "manual_company_type_review",
}

WARNINGS = {
    "bank": "Do not compare a bank directly with standard industrial equities.",
    "insurance": "Insurance company analysis requires insurance-specific fields.",
    "reit": "REITs require AFFO/FFO/NAV; standard equity ranking is degraded.",
    "fund_etf_excluded": "Funds/ETFs are not targets for company Snowflake checks.",
    "utility": "Use regulated-utility sector context before ranking.",
    "commodity_cyclical": "Commodity cyclicals require cycle/commodity-price context before ranking.",
    "saas": "SaaS interpretation should review SBC, growth durability and FCF conversion.",
    "pharma": "Pharma/biotech interpretation requires pipeline and R&D context.",
    "adr_foreign": "Foreign/ADR issuers require filing, currency and primary-listing review.",
    "loss_making": "Loss-making companies require cash-runway context before valuation conclusions.",
    "unknown": "Company type is insufficiently documented; do not rank without manual review.",
}


def _text_blob(output: Dict[str, Any], input_payload: Dict[str, Any] | None, identifier_record: Mapping[str, Any] | None) -> str:
    parts = []
    for obj in (input_payload or {}, output, identifier_record or {}):
        for key in (
            "ticker", "exchange", "company_type", "sector", "industry", "security_type",
            "valuation_model", "valuation_variant", "sic", "sic_description", "is_adr", "is_foreign_issuer",
        ):
            if obj.get(key) is not None:
                parts.append(str(obj.get(key)))
    return " ".join(parts).lower()


def _normalized_company_type(identifier_record: Mapping[str, Any] | None, input_payload: Dict[str, Any] | None, output: Dict[str, Any]) -> str:
    for obj in (identifier_record or {}, input_payload or {}, output):
        value = obj.get("company_type") or obj.get("security_type")
        if value:
            return str(value).strip().lower()
    return ""


def _detect_company_type(
    output: Dict[str, Any],
    input_payload: Dict[str, Any] | None,
    identifier_record: Mapping[str, Any] | None,
) -> tuple[str, list[str]]:
    raw = _normalized_company_type(identifier_record, input_payload, output)
    blob = _text_blob(output, input_payload, identifier_record)
    reasons: list[str] = []
    if identifier_record:
        reasons.append("IDENTIFIER_MASTER_RECORD_USED")
    if raw in {"fund", "etf", "mutual_fund", "closed_end_fund"} or " etf" in f" {blob}" or "fund" in blob:
        return "fund_etf_excluded", reasons + ["SECURITY_TYPE_INDICATES_FUND_OR_ETF"]
    if raw in {"bank", "financial", "financials", "financial_institution"} or "bank" in blob or "deposits" in blob:
        return "bank", reasons + ["COMPANY_TYPE_OR_TEXT_INDICATES_BANK_OR_FINANCIAL"]
    if raw in {"insurance", "insurer"} or "insurance" in blob or "insurer" in blob:
        return "insurance", reasons + ["COMPANY_TYPE_OR_TEXT_INDICATES_INSURANCE"]
    if raw == "reit" or "reit" in blob or output.get("valuation_model") == "affo_dcf":
        return "reit", reasons + ["COMPANY_TYPE_OR_MODEL_INDICATES_REIT"]
    if bool(str((identifier_record or {}).get("is_adr", "")).lower() in {"true", "1", "yes"}) or " adr" in f" {blob}" or "foreign issuer" in blob:
        return "adr_foreign", reasons + ["IDENTIFIER_OR_TEXT_INDICATES_ADR_FOREIGN_ISSUER"]
    if raw in {"utility", "utilities"} or "utility" in blob or "utilities" in blob:
        return "utility", reasons + ["TEXT_INDICATES_UTILITY"]
    if raw in {"commodity", "cyclical", "commodity_cyclical"} or any(token in blob for token in ("oil", "gas", "mining", "energy")):
        return "commodity_cyclical", reasons + ["TEXT_INDICATES_COMMODITY_CYCLICAL"]
    if raw in {"saas", "software_as_a_service"} or "saas" in blob:
        return "saas", reasons + ["TEXT_INDICATES_SAAS"]
    if raw in {"pharma", "biotech", "pharmaceutical"} or any(token in blob for token in ("pharma", "biotech", "biotechnology")):
        return "pharma", reasons + ["TEXT_INDICATES_PHARMA_OR_BIOTECH"]
    if raw in {"loss_making", "loss-making"}:
        return "loss_making", reasons + ["COMPANY_TYPE_INDICATES_LOSS_MAKING"]
    if raw in {"non_financial", "standard", "industrial", "standard_industrial", "common"}:
        return "standard_industrial", reasons + ["COMPANY_TYPE_INDICATES_STANDARD_EQUITY"]
    if output.get("valuation_model") in {"two_stage_fcf", "ddm"}:
        return "standard_industrial", reasons + ["VALUATION_MODEL_COMPATIBLE_WITH_STANDARD_EQUITY"]
    return "unknown", reasons + ["INSUFFICIENT_COMPANY_TYPE_METADATA"]


def assess_model_applicability(
    output: Dict[str, Any],
    *,
    input_payload: Dict[str, Any] | None = None,
    audit_policies: Mapping[str, Any] | None = None,
    identifier_master_records: Iterable[Dict[str, Any]] | None = None,
    identifier_master_path: str | None = None,
) -> Dict[str, Any]:
    policies = audit_policies or load_audit_policies()
    identifier_record = find_identifier_record(
        output.get("ticker") or (input_payload or {}).get("ticker"),
        output.get("exchange") or (input_payload or {}).get("exchange"),
        records=identifier_master_records,
        path=identifier_master_path or "data/real_sources/reference/identifier_master.csv",
    )
    company_type, detection_reasons = _detect_company_type(output, input_payload, identifier_record)
    valuation_model = output.get("valuation_model")
    policy = (policies.get("model_applicability") or {})
    allowed_map = policy.get("allowed_score_usage") or {}
    reason_map = policy.get("reason_codes") or {}
    if company_type == "standard_industrial":
        status = STANDARD_OK
    elif company_type == "fund_etf_excluded":
        status = NOT_APPLICABLE
    elif company_type == "unknown":
        status = UNKNOWN
    else:
        status = DEGRADED if company_type in {"bank", "insurance", "reit", "utility", "commodity_cyclical", "pharma", "adr_foreign", "loss_making"} else STANDARD_OK
    reason_code = str(reason_map.get(company_type) or _default_reason(company_type, status))
    allowed = str(allowed_map.get(company_type) or (RANKABLE if status == STANDARD_OK else policy.get("default_unknown_usage", AUDIT_ONLY)))
    if status == NOT_APPLICABLE:
        allowed = DO_NOT_COMPARE
    recommended = RECOMMENDED_MODELS.get(company_type, RECOMMENDED_MODELS["unknown"])
    if company_type == "standard_industrial" and valuation_model:
        recommended = str(valuation_model)
    comparability_warning = WARNINGS.get(company_type)
    return {
        "status": status,
        "company_type_detected": company_type,
        "reason_code": reason_code,
        "recommended_model": recommended,
        "allowed_score_usage": allowed,
        "comparability_warning": comparability_warning,
        "valuation_model": valuation_model,
        "valuation_variant": output.get("valuation_variant"),
        "detection_reasons": detection_reasons,
        "identifier_master_used": bool(identifier_record),
        "identifier_record": _safe_identifier_record(identifier_record),
        "source_quality": "exact_or_approximation" if identifier_record else ("approximation" if company_type != "unknown" else "missing"),
        "source_class": "E2/E3" if identifier_record else "E3",
        "input_lineage": {
            "company_type": (identifier_record or {}).get("company_type") or (input_payload or {}).get("company_type") or output.get("company_type"),
            "security_type": (identifier_record or {}).get("security_type") or (input_payload or {}).get("security_type"),
            "valuation_model": valuation_model,
            "industry": (identifier_record or {}).get("industry") or (input_payload or {}).get("industry"),
            "sector": (identifier_record or {}).get("sector") or (input_payload or {}).get("sector"),
            "identifier_master": bool(identifier_record),
        },
    }


def _default_reason(company_type: str, status: str) -> str:
    if company_type == "standard_industrial":
        return "STANDARD_EQUITY_MODEL_APPLICABLE"
    if company_type == "unknown" or status == UNKNOWN:
        return "MODEL_APPLICABILITY_UNKNOWN"
    return f"{company_type.upper()}_REQUIRES_CONTEXTUAL_INTERPRETATION"


def _safe_identifier_record(record: Mapping[str, Any] | None) -> Dict[str, Any] | None:
    if not record:
        return None
    allowed = {"ticker", "exchange", "country", "currency", "CIK", "cik", "LEI", "lei", "security_type", "company_type", "is_adr", "is_foreign_issuer", "sic", "sic_description"}
    return {str(k): v for k, v in record.items() if k in allowed or str(k) in allowed}
