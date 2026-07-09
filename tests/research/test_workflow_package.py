import json
from pathlib import Path

from jsonschema import validate

from sws_engine.research.workflow_package import (
    build_workflow_package,
    render_workflow_package_report_md,
    workflow_package_from_files,
    write_workflow_package_artifacts,
)

FIX = Path("tests/fixtures/workflow_package")
SCHEMA = Path("schemas/aux/workflow_package.schema.json")


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_workflow_package_schema_and_unknown_preservation():
    package = workflow_package_from_files(
        audit_summary_path=FIX / "AAPL_audit_summary.json",
        explanations_path=FIX / "AAPL_explanations.json",
        sensitivity_path=FIX / "AAPL_sensitivity_summary.json",
        business_risk_path=FIX / "AAPL_business_risk_package.json",
        thesis_status_path=FIX / "AAPL_thesis_status.json",
        decision_record_path=FIX / "AAPL_decision_record.json",
        portfolio_audit_path=FIX / "core_portfolio_audit.json",
        run_comparison_path=FIX / "AAPL_run_comparison.json",
        workflow_id="p13-aapl",
    )
    validate(instance=package, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert package["schema_version"] == "workflow_package.v0.1"
    assert package["ticker"] == "AAPL"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["reason_code"] == "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED"
    assert package["unknown_summary"]["total_unknown_indicators"] > 0
    assert package["recommendation_language_absent"] is True
    assert package["not_investment_advice"] is True


def test_workflow_package_missing_optional_is_visible():
    package = build_workflow_package(audit_summary=_load("AAPL_audit_summary.json"), workflow_id="partial")
    statuses = {row["component_id"]: row["status"] for row in package["component_status"]}
    assert statuses["audit_summary"] in {"READY", "UNKNOWN_PRESENT"}
    assert statuses["sensitivity_summary"] == "MISSING_OPTIONAL"
    assert package["readiness_summary"]["missing_optional_count"] >= 1
    assert package["readiness_summary"]["missing_required_count"] == 0


def test_workflow_package_missing_required_returns_unknown():
    package = build_workflow_package(audit_summary=None, workflow_id="missing")
    assert package["status"] == "UNKNOWN"
    assert package["reason_code"] == "WORKFLOW_PACKAGE_INPUTS_MISSING"
    assert package["readiness_summary"]["missing_required_count"] == 1


def test_workflow_package_report_contains_guardrails(tmp_path):
    package = workflow_package_from_files(audit_summary_path=FIX / "AAPL_audit_summary.json")
    paths = write_workflow_package_artifacts(package, tmp_path)
    report = Path(paths["workflow_package_report"]).read_text(encoding="utf-8")
    obj = json.loads(Path(paths["workflow_package_json"]).read_text(encoding="utf-8"))
    assert obj["recommendation_language_absent"] is True
    assert "What remains UNKNOWN" in report
    assert "Not investment advice" in report
    assert "BUY" not in report
    assert "SELL" not in report
    # Direct renderer smoke too.
    assert "Research Workflow Package" in render_workflow_package_report_md(package)
