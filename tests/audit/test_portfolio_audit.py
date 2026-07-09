import json
from pathlib import Path

from jsonschema import validate

from sws_engine.audit.portfolio_audit import (
    build_portfolio_audit,
    load_holdings_csv,
    portfolio_audit_from_files,
    render_portfolio_audit_report_md,
)


def test_portfolio_audit_schema_and_weighted_outputs():
    package = portfolio_audit_from_files(
        "tests/fixtures/portfolio_audit/holdings.csv",
        audit_dir="tests/fixtures/portfolio_audit/audits",
        business_risk_dir="tests/fixtures/portfolio_audit/business_risks",
        thesis_dir="tests/fixtures/portfolio_audit/theses",
        sensitivity_dir="tests/fixtures/portfolio_audit/sensitivity",
        portfolio_id="core",
        valuation_date="2026-07-09",
    )
    schema = json.loads(Path("schemas/aux/portfolio_audit.schema.json").read_text(encoding="utf-8"))
    validate(package, schema)
    assert package["schema_version"] == "portfolio_audit.v0.1"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["portfolio_id"] == "core"
    assert package["holdings_count"] == 5
    assert package["weighted_data_confidence"]["level"] == "MEDIUM"
    assert package["weighted_conclusion_risk"]["level"] == "MEDIUM"
    assert package["unknown_exposure"]["weight_pct"] == 10.0
    assert package["provider_degradation_exposure"]["weight_pct"] == 45.0
    assert package["sector_concentration"]["top_bucket"] == "Technology"
    assert package["single_thesis_concentration"]["top_bucket"] == "AI_device_ecosystem"
    assert package["macro_sensitivity_map"]["top_exposure"] == "rates"
    assert package["not_investment_advice"] is True


def test_portfolio_audit_unknown_artifacts_preserved():
    package = portfolio_audit_from_files("tests/fixtures/portfolio_audit/missing_holdings.csv", audit_dir="tests/fixtures/portfolio_audit/audits")
    assert package["status"] == "UNKNOWN"
    assert package["reason_code"] == "PORTFOLIO_AUDIT_ARTIFACTS_MISSING"
    assert package["unknown_exposure"]["weight_pct"] == 100.0
    assert all(row["artifact_status"] == "UNKNOWN" for row in package["holdings"])


def test_portfolio_audit_report_guardrails():
    package = portfolio_audit_from_files(
        "tests/fixtures/portfolio_audit/holdings.csv",
        audit_dir="tests/fixtures/portfolio_audit/audits",
        portfolio_id="core",
    )
    md = render_portfolio_audit_report_md(package)
    assert "Portfolio Audit Report" in md
    assert "Not investment advice" in md
    assert not any(token in md for token in [" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD"])


def test_portfolio_audit_api_payload_basic():
    holdings = load_holdings_csv("tests/fixtures/portfolio_audit/holdings.csv")
    package = build_portfolio_audit(holdings, portfolio_id="inline")
    assert package["portfolio_id"] == "inline"
    assert package["unknown_exposure"]["weight_pct"] == 95.0  # cash is excluded from invested unknown exposure
