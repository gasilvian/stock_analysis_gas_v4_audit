import json
from pathlib import Path

from jsonschema import validate

from sws_engine.research.watchlist import audit_watchlist_from_files, render_watchlist_report_md


def test_watchlist_audit_schema_and_bucket_triage():
    package = audit_watchlist_from_files(
        "tests/fixtures/watchlist/watchlist.csv",
        audit_dir="tests/fixtures/watchlist/audits",
        business_risk_dir="tests/fixtures/watchlist/business_risks",
    )
    schema = json.loads(Path("schemas/aux/watchlist_audit.schema.json").read_text(encoding="utf-8"))
    validate(package, schema)

    by_ticker = {item["ticker"]: item for item in package["items"]}
    assert by_ticker["AAPL"]["bucket"] == "Researchable Now"
    assert by_ticker["AAPL"]["manual_review_required"] is False
    assert by_ticker["JPM"]["bucket"] == "Needs Different Model"
    assert "WATCHLIST_NEEDS_DIFFERENT_MODEL" in by_ticker["JPM"]["reason_codes"]
    assert "WATCHLIST_PROVIDER_DEGRADED" in by_ticker["JPM"]["reason_codes"]
    assert by_ticker["MISS"]["bucket"] == "Data Limited"
    assert by_ticker["MISS"]["artifact_status"] == "UNKNOWN"
    assert package["not_investment_advice"] is True


def test_watchlist_research_queue_and_unknown_preserved():
    package = audit_watchlist_from_files(
        "tests/fixtures/watchlist/watchlist.csv",
        audit_dir="tests/fixtures/watchlist/audits",
    )
    assert package["unknown_artifact_count"] == 1
    assert package["research_queue"][0]["ticker"] == "AAPL"
    assert any(item["ticker"] == "MISS" and item["artifact_status"] == "UNKNOWN" for item in package["items"])


def test_watchlist_report_has_footer_and_no_recommendation_language():
    package = audit_watchlist_from_files(
        "tests/fixtures/watchlist/watchlist.csv",
        audit_dir="tests/fixtures/watchlist/audits",
    )
    md = render_watchlist_report_md(package)
    assert "Watchlist Audit Report" in md
    assert "Not investment advice" in md
    assert "What we don't know" not in md  # watchlist has its own triage sections
    forbidden = {" BUY ", " SELL ", " HOLD "}
    assert not any(word in md for word in forbidden)
