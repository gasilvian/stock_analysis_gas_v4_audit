"""Deterministic explainability layer for v4.0 audit artifacts."""
from sws_engine.explain.dictionary import (
    DEFAULT_REASON_CODE_DICTIONARY,
    REQUIRED_REASON_CODES,
    load_reason_code_dictionary,
    validate_reason_code_dictionary,
)
from sws_engine.explain.check_explainer import (
    explain_check,
    explain_checks,
    explain_audit_summary,
    build_explanation_package,
    explanation_report_md,
    write_explanation_artifacts,
)

__all__ = [
    "DEFAULT_REASON_CODE_DICTIONARY",
    "REQUIRED_REASON_CODES",
    "load_reason_code_dictionary",
    "validate_reason_code_dictionary",
    "explain_check",
    "explain_checks",
    "explain_audit_summary",
    "build_explanation_package",
    "explanation_report_md",
    "write_explanation_artifacts",
]
