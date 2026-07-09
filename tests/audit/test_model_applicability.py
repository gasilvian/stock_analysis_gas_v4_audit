import json
from pathlib import Path

from sws_engine.audit.model_applicability import assess_model_applicability


def _output():
    return json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))


def test_model_applicability_standard_ok():
    out = _output()
    audit = assess_model_applicability(out, input_payload={"company_type": "non_financial", "industry": "Software"})
    assert audit["status"] == "STANDARD_OK"
    assert audit["allowed_score_usage"] == "rankable"


def test_model_applicability_bank_degraded():
    out = _output()
    audit = assess_model_applicability(out, input_payload={"company_type": "bank", "industry": "Banks"})
    assert audit["status"] == "DEGRADED"
    assert audit["reason_code"] == "BANK_STANDARD_FCF_MODEL_LIMITED"
    assert audit["allowed_score_usage"] == "do_not_compare"


def test_model_applicability_reit_degraded():
    out = _output()
    audit = assess_model_applicability(out, input_payload={"company_type": "reit", "industry": "REIT"})
    assert audit["status"] == "DEGRADED"
    assert audit["reason_code"] == "REIT_REQUIRES_AFFO_FFO_NAV"
    assert audit["allowed_score_usage"] == "audit_only"


def test_model_applicability_etf_not_applicable():
    out = _output()
    audit = assess_model_applicability(out, input_payload={"company_type": "etf", "security_type": "ETF"})
    assert audit["status"] == "NOT_APPLICABLE"
    assert audit["reason_code"] == "FUND_NOT_COMPANY_ANALYSIS_TARGET"
