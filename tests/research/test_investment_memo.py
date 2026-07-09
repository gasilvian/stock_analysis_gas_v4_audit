import json
from pathlib import Path

from jsonschema import validate

from sws_engine.reporting.investment_memo import (
    build_investment_memo_package,
    investment_memo_from_files,
    render_investment_memo_md,
)

FIX = Path("tests/fixtures/investment_memo")


def test_investment_memo_schema_and_guardrails():
    package = investment_memo_from_files(
        audit_summary_path=FIX / "AAPL_audit_summary.json",
        explanations_path=FIX / "AAPL_explanations.json",
        sensitivity_path=FIX / "AAPL_sensitivity_summary.json",
        business_risk_path=FIX / "AAPL_business_risk_package.json",
        thesis_status_path=FIX / "AAPL_thesis_status.json",
        decision_record_path=FIX / "AAPL_decision_record.json",
        portfolio_audit_path=FIX / "core_portfolio_audit.json",
    )
    schema = json.loads(Path("schemas/aux/investment_memo.schema.json").read_text(encoding="utf-8"))
    validate(package, schema)
    assert package["schema_version"] == "investment_memo.v0.1"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["ticker"] == "AAPL"
    assert package["recommendation_language_absent"] is True
    assert package["false_precision_guardrail"]["reason_code"] == "MEMO_FALSE_PRECISION_GUARDRAIL_APPLIED"
    assert package["unknown_summary"]["unknown_checks_count"] == 5
    assert "optional_component_missing" not in " ".join(package["unknown_summary"]["critical_missing_inputs"])
    assert package["sections"]["thesis_status"]["thesis_status"] == "WATCH"
    md = render_investment_memo_md(package)
    assert "Investment Research Audit Memo" in md
    assert "What remains UNKNOWN" in md
    assert "Not investment advice" in md
    assert not any(token in md for token in [" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "target price"])


def test_investment_memo_optional_components_remain_unknown():
    package = investment_memo_from_files(audit_summary_path=FIX / "AAPL_audit_summary.json")
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["component_status"]["reason_code"] == "MEMO_COMPONENT_UNKNOWN"
    assert "sensitivity_summary" in package["component_status"]["missing_components"]
    assert any("Optional component missing" in item for item in package["manual_review_items"])
    assert package["unknown_summary"]["reason_code"] == "MEMO_UNKNOWN_PRESERVED"


def test_investment_memo_missing_audit_summary_unknown():
    package = build_investment_memo_package(audit_summary=None)
    assert package["status"] == "UNKNOWN"
    assert package["reason_code"] == "MEMO_INPUTS_MISSING"
    assert package["not_investment_advice"] is True
