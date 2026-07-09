from __future__ import annotations

import pytest

from dashboard.components.badges import badge_kind
from dashboard.components.checks_table import validate_check_contract
from dashboard.components.snowflake_radar import extract_radar_rows, validate_scores_have_coverage
from dashboard.components.warnings_panel import classify_warning, has_important_warnings
from dashboard.components.audit_workflow import extract_workflow_rows, validate_workflow_package, workflow_readiness_label


def _scores():
    return {
        axis: {
            "score_raw": idx,
            "known_checks_count": 6,
            "unknown_checks_count": 0,
            "coverage_pct": 1.0,
        }
        for idx, axis in enumerate(["value", "future", "past", "health", "dividend"], start=1)
    }


def _check():
    return {
        "axis": "value",
        "id": 1,
        "name": "trading_below_fair_value_20pct",
        "result": "PASS",
        "reason_code": "OK",
        "source_quality": "exact",
        "source_class": "E0",
        "inputs": {},
        "threshold": "Price <= FV * 0.8",
        "input_lineage": {},
    }


def test_radar_extracts_score_and_requires_coverage():
    rows = extract_radar_rows(_scores())
    assert len(rows) == 5
    assert rows[0]["coverage_pct"] == 1.0
    assert validate_scores_have_coverage(_scores()) is True


def test_radar_rejects_missing_coverage():
    scores = _scores()
    del scores["value"]["coverage_pct"]
    with pytest.raises(ValueError):
        extract_radar_rows(scores)


def test_check_contract_validation():
    assert validate_check_contract(_check()) is True
    bad = _check()
    del bad["input_lineage"]
    with pytest.raises(ValueError):
        validate_check_contract(bad)


def test_warning_classification():
    warnings = ["PROVIDER_LIMITATION: missing FCF", "general note"]
    assert classify_warning(warnings[0]) == "important"
    assert has_important_warnings(warnings) is True


def test_provider_and_result_badge_classification():
    assert badge_kind("yfinance_pragmatic") == "warning"
    assert badge_kind("sws_public_faithful_manual_inputs") == "success"
    assert badge_kind("UNKNOWN") == "warning"
    assert badge_kind("FAIL") == "error"


def test_audit_workflow_component_helpers():
    package = {
        "schema_version": "workflow_package.v0.1",
        "status": "PASS_WITH_LIMITATIONS",
        "reason_code": "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED",
        "component_status": [
            {"component_id": "audit_summary", "label": "Company Audit", "status": "UNKNOWN_PRESENT", "required": True, "reason_code": "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED", "unknown_indicators_count": 2, "api_method": "GET", "api_path": "/companies/AAPL/audit"}
        ],
        "workflow_steps": [],
        "readiness_summary": {"manual_review_count": 1, "missing_required_count": 0},
        "unknown_summary": {"total_unknown_indicators": 2},
        "not_investment_advice": True,
        "recommendation_language_absent": True,
    }
    assert validate_workflow_package(package) is True
    assert workflow_readiness_label(package) == "MANUAL_REVIEW"
    rows = extract_workflow_rows(package)
    assert rows[0]["component"] == "audit_summary"
    assert rows[0]["api_path"] == "/companies/AAPL/audit"
