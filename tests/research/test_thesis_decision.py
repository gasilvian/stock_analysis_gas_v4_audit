import json
from pathlib import Path

from jsonschema import validate

from sws_engine.research.journal import build_decision_record, load_journal, record_decision_from_files
from sws_engine.research.thesis import evaluate_thesis_from_files, render_thesis_report_md


def test_thesis_status_schema_and_on_track():
    package = evaluate_thesis_from_files(
        "tests/fixtures/thesis_decision/AAPL_thesis.yaml",
        audit_summary_path="tests/fixtures/thesis_decision/AAPL_audit_summary.json",
    )
    schema = json.loads(Path("schemas/aux/thesis_status.schema.json").read_text(encoding="utf-8"))
    validate(package, schema)
    assert package["ticker"] == "AAPL"
    assert package["thesis_status"] == "ON_TRACK"
    assert package["reason_code"] == "THESIS_ON_TRACK"
    assert package["rules_summary"]["ok"] == 3
    assert package["not_investment_advice"] is True


def test_thesis_status_broken_and_unknown_preserved():
    package = evaluate_thesis_from_files(
        "tests/fixtures/thesis_decision/BROKEN_thesis.yaml",
        audit_summary_path="tests/fixtures/thesis_decision/JPM_audit_summary.json",
    )
    assert package["ticker"] == "JPM"
    assert package["thesis_status"] == "BROKEN"
    assert package["reason_code"] == "THESIS_INVALIDATION_TRIGGERED"
    assert package["rules_summary"]["triggered"] == 2
    assert any("rankable_required" in item for item in package["manual_review_items"])


def test_thesis_status_majority_unknown_degrades_to_unknown():
    package = evaluate_thesis_from_files("tests/fixtures/thesis_decision/AAPL_thesis.yaml")
    assert package["thesis_status"] == "UNKNOWN"
    assert package["reason_code"] == "THESIS_MAJORITY_RULES_UNKNOWN"
    assert package["rules_summary"]["unknown"] == 3


def test_thesis_report_has_footer_and_no_recommendation_language():
    package = evaluate_thesis_from_files(
        "tests/fixtures/thesis_decision/AAPL_thesis.yaml",
        audit_summary_path="tests/fixtures/thesis_decision/AAPL_audit_summary.json",
    )
    md = render_thesis_report_md(package)
    assert "Thesis Status Report" in md
    assert "Not investment advice" in md
    assert not any(word in md for word in {" BUY ", " SELL ", " HOLD "})


def test_decision_journal_schema_record_and_forbidden_type(tmp_path):
    journal = tmp_path / "decisions.jsonl"
    record = record_decision_from_files(
        "tests/fixtures/thesis_decision/AAPL_decision.yaml",
        journal,
        audit_summary_path="tests/fixtures/thesis_decision/AAPL_audit_summary.json",
    )
    schema = json.loads(Path("schemas/aux/decision_journal.schema.json").read_text(encoding="utf-8"))
    validate(record, schema)
    assert record["status"] == "PASS"
    assert record["decision_type"] == "research_deeper"
    assert record["data_confidence_at_decision"] == "HIGH"
    assert load_journal(journal)[0]["decision_id"] == record["decision_id"]

    forbidden = build_decision_record({"ticker": "AAPL", "decision_type": "buy"})
    validate(forbidden, schema)
    assert forbidden["status"] == "UNKNOWN"
    assert forbidden["reason_code"] == "DECISION_TYPE_NOT_ALLOWED"
    assert len(load_journal(journal)) == 1  # forbidden decision was not appended
