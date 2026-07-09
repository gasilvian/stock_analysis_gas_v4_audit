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


def test_memo_component_reason_code_not_falsely_unknown_for_plural_codes():
    """P1.0 regression: real audit summaries emit reason_codes (plural) for
    data_confidence and no top-level reason code for conclusion_risk. The memo
    must not mislabel these fully present components as MEMO_COMPONENT_UNKNOWN."""
    audit_summary = json.loads((FIX / "AAPL_audit_summary.json").read_text(encoding="utf-8"))
    # Reshape to the real audit-summary shape: plural list, no singular code.
    dc = audit_summary["data_confidence"]
    dc.pop("reason_code", None)
    dc["reason_codes"] = ["LOW_FIELD_LINEAGE_COVERAGE"]
    audit_summary.get("conclusion_risk", {}).pop("reason_code", None)
    audit_summary.get("conclusion_risk", {}).pop("reason_codes", None)

    package = build_investment_memo_package(audit_summary=audit_summary)
    dc_section = package["sections"]["data_confidence"]
    cr_section = package["sections"]["conclusion_risk"]
    assert dc_section["reason_code"] == "LOW_FIELD_LINEAGE_COVERAGE"
    assert dc_section["reason_codes"] == ["LOW_FIELD_LINEAGE_COVERAGE"]
    assert dc_section["reason_code"] != "MEMO_COMPONENT_UNKNOWN"
    # Component present but without its own code: truthful PRESENT, not UNKNOWN.
    assert cr_section["reason_code"] == "MEMO_COMPONENT_PRESENT"


def test_memo_source_quality_inherits_from_data_confidence_mix():
    """P1.2-cal (B2) regression: real calibration showed 'Source quality:
    UNKNOWN' in every memo because the audit summary carries its quality
    signal in data_confidence.source_quality_mix, not in a top-level key.
    The memo must inherit the dominant non-missing quality, let declared
    component qualities act as weakest link, and never let silent
    components drag the aggregate to UNKNOWN."""
    audit_summary = json.loads((FIX / "AAPL_audit_summary.json").read_text(encoding="utf-8"))
    audit_summary.pop("source_quality", None)
    audit_summary.setdefault("data_confidence", {})["source_quality_mix"] = {
        "approximation": 12, "missing": 18}

    package = build_investment_memo_package(audit_summary=audit_summary)
    assert package["source_quality"] == "approximation"

    # A component that declares a weaker quality wins (weakest link).
    package2 = build_investment_memo_package(
        audit_summary=audit_summary,
        sensitivity_summary={"ticker": package["ticker"], "status": "UNKNOWN",
                             "source_quality": "assumption"})
    assert package2["source_quality"] == "assumption"

    # Nothing known anywhere -> honest UNKNOWN, never invented.
    bare = {k: v for k, v in audit_summary.items() if k != "data_confidence"}
    package3 = build_investment_memo_package(audit_summary=bare)
    assert package3["source_quality"] == "UNKNOWN"
