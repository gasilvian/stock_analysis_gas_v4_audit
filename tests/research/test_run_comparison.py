import json
from pathlib import Path

from jsonschema import validate

from sws_engine.research.run_comparison import (
    build_run_comparison_package,
    run_comparison_from_files,
    write_run_comparison_artifacts,
)

FIX = Path("tests/fixtures/run_comparison")
SCHEMA = Path("schemas/aux/run_comparison.schema.json")


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_run_comparison_schema_and_unknown_preservation():
    package = run_comparison_from_files(
        previous_path=FIX / "AAPL_previous_audit_summary.json",
        current_path=FIX / "AAPL_current_audit_summary.json",
        comparison_id="aapl-p12",
    )
    validate(instance=package, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert package["ticker"] == "AAPL"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["reason_code"] == "RUN_COMPARISON_UNKNOWN_PRESERVED"
    assert package["unknown_changes"]["current_unknown_checks_count"] == 5
    assert "fcf_estimates" in package["unknown_changes"]["critical_missing_inputs_added"]
    assert package["checks_changes"]["new_unknown_count"] == 2
    assert package["metadata_changes"]["assumptions_hash_changed"] is True
    assert package["metadata_changes"]["provider_profile_changed"] is True
    assert package["recommendation_language_absent"] is True


def test_run_comparison_detects_score_and_lineage_changes():
    package = build_run_comparison_package(
        _load("AAPL_previous_audit_summary.json"),
        _load("AAPL_current_audit_summary.json"),
    )
    assert package["score_changes"]["changed_count"] >= 2
    assert package["lineage_changes"]["changed_count"] >= 1
    assert any("Assumptions hash changed" in item for item in package["manual_review_items"])
    assert any("lineage" in item.lower() for item in package["manual_review_items"])


def test_run_comparison_no_material_change_but_unknown_visible_if_present():
    package = build_run_comparison_package(
        _load("AAPL_previous_audit_summary.json"),
        _load("AAPL_unchanged_audit_summary.json"),
    )
    assert package["material_change_count"] == 0
    assert package["reason_code"] == "RUN_COMPARISON_UNKNOWN_PRESERVED"
    assert package["unknown_changes"]["current_unknown_checks_count"] == 3


def test_run_comparison_markdown_report_contains_guardrails(tmp_path):
    package = run_comparison_from_files(
        previous_path=FIX / "AAPL_previous_audit_summary.json",
        current_path=FIX / "AAPL_current_audit_summary.json",
    )
    paths = write_run_comparison_artifacts(package, tmp_path)
    json_out = json.loads(Path(paths["comparison_json"]).read_text(encoding="utf-8"))
    report = Path(paths["comparison_report"]).read_text(encoding="utf-8")
    assert json_out["recommendation_language_absent"] is True
    assert "UNKNOWN" in report
    assert "Not investment advice" in report
    assert "BUY" not in report
    assert "SELL" not in report
