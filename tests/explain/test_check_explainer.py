import json
from pathlib import Path

from jsonschema import validate

from sws_engine.audit.audit_summary import build_audit_summary
from sws_engine.explain.check_explainer import build_explanation_package, explain_check, explanation_report_md


def _output_with_unknown():
    out = json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))
    out["checks"][0]["result"] = "UNKNOWN"
    out["checks"][0]["reason_code"] = "MISSING_INPUT"
    out["checks"][0]["source_quality"] = "missing"
    return out


def test_explain_check_renders_reason_code_and_inputs():
    check = _output_with_unknown()["checks"][0]
    exp = explain_check(check, mode="analyst")
    assert exp["reason_code"] == "MISSING_INPUT"
    assert exp["known_reason_code"] is True
    assert "MISSING_INPUT" in exp["explanation"] or "missing" in exp["explanation"].lower()
    assert exp["remediation_hint"]


def test_explanation_package_schema_valid_and_preserves_unknown():
    out = _output_with_unknown()
    audit = build_audit_summary(out, input_payload={"company_type": "non_financial"}, run_id="run-explain")
    package = build_explanation_package(out, audit_summary=audit, mode="plain_english")
    schema = json.loads(Path("schemas/aux/explanation_package.schema.json").read_text(encoding="utf-8"))
    validate(package, schema)
    assert package["unknown_checks_count"] == 1
    assert package["checks_explained_count"] >= 1
    assert package["check_explanations"][0]["mode"] == "plain_english"
    assert package["not_investment_advice"] is True


def test_explanation_report_has_no_buy_sell_hold_language():
    out = _output_with_unknown()
    package = build_explanation_package(out, mode="analyst")
    md = explanation_report_md(package)
    assert "Not investment advice" in md
    forbidden = {"BUY", "SELL", "HOLD"}
    assert not any(f" {word} " in md for word in forbidden)
