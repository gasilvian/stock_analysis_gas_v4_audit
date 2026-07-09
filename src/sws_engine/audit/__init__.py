"""Audit layer v4.0 auxiliary modules.

The audit layer consumes already validated SWS Engine v3.1 outputs and produces
auxiliary research-audit artifacts. It does not change checks, valuation,
growth, portfolio logic, or ``schemas/output_schema.json``.
"""

from sws_engine.audit.audit_summary import build_audit_summary
from sws_engine.audit.audit_report import audit_report_md, write_audit_artifacts
from sws_engine.audit.conclusion_risk import assess_conclusion_risk
from sws_engine.audit.data_confidence import assess_data_confidence
from sws_engine.audit.model_applicability import assess_model_applicability
from sws_engine.audit.risk_signals import build_business_risk_package
from sws_engine.audit.portfolio_audit import build_portfolio_audit

__all__ = [
    "assess_data_confidence",
    "assess_model_applicability",
    "assess_conclusion_risk",
    "build_audit_summary",
    "audit_report_md",
    "write_audit_artifacts",
    "build_business_risk_package",
    "build_portfolio_audit",
]
