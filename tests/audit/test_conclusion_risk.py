import json
from pathlib import Path

from sws_engine.audit.audit_summary import build_audit_summary


def _output():
    return json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))


def test_conclusion_risk_low_for_complete_standard_fixture():
    out = _output()
    summary = build_audit_summary(out, input_payload={"company_type": "non_financial"})
    assert summary["conclusion_risk"]["risk_level"] == "LOW"


def test_conclusion_risk_high_when_unknown_many():
    out = _output()
    for check in out["checks"][:12]:
        check["result"] = "UNKNOWN"
        check["reason_code"] = "MISSING_FCF_ESTIMATES"
        check["source_quality"] = "missing"
    summary = build_audit_summary(out, input_payload={"company_type": "non_financial"})
    assert summary["conclusion_risk"]["risk_level"] == "HIGH"
    assert any(d["reason_code"] == "MANY_UNKNOWN_CHECKS" for d in summary["conclusion_risk"]["drivers"])


def test_conclusion_risk_high_for_model_degraded_bank():
    out = _output()
    summary = build_audit_summary(out, input_payload={"company_type": "bank", "industry": "Banks"})
    assert summary["model_applicability"]["status"] == "DEGRADED"
    assert summary["conclusion_risk"]["risk_level"] == "HIGH"
