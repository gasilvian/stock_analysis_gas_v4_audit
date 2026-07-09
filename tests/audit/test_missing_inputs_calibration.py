"""P1.2-cal regression tests for backlog B1 (real-calibration findings).

The 2026-07-10 real-data calibration (10 tickers) exposed two layers of a
missing-input misattribution bug around risk_free_rate_10y_5y_avg:

1. Keyword inference used the generic token "rate", so an UNKNOWN check that
   merely mentioned savings_rate attributed a missing risk-free rate — a
   false positive present even when the curated rate was injected.
2. The classifier never consulted the payload, so it could neither clear a
   field that was demonstrably present nor genuinely detect the root cause
   (a missing rate manifests as fair_value=None in value-axis checks, never
   by name).

These tests pin the fixed behavior in both directions.
"""
from sws_engine.audit.missing_inputs import classify_missing_inputs


def _payload(with_rate: bool, lineage_quality: str = "assumption"):
    payload = {
        "ticker": "DEMO",
        "lineage": {"field_lineage": {}},
    }
    if with_rate:
        payload["risk_free_rate_10y_5y_avg"] = 0.03765
        payload["lineage"]["field_lineage"]["risk_free_rate_10y_5y_avg"] = {
            "provider": "curated_rates",
            "source_quality": lineage_quality,
            "source_class": "E2",
        }
    return payload


def _unknown_check(check_id, name, inputs, reason_code="MISSING_INPUT", axis="value"):
    return {"id": check_id, "axis": axis, "name": name, "result": "UNKNOWN",
            "reason_code": reason_code, "inputs": inputs}


def test_present_curated_rate_is_never_reported_missing():
    """B1 layer 1: 'savings_rate' in an unrelated UNKNOWN check must not
    attribute a missing risk-free rate when the payload carries the value."""
    checks = [
        _unknown_check("1", "Earnings vs savings", {"earnings_growth": None, "savings_rate": 0.02}),
    ]
    fields = {r["field"] for r in classify_missing_inputs(checks, input_payload=_payload(with_rate=True))}
    assert "risk_free_rate_10y_5y_avg" not in fields


def test_savings_rate_alone_no_longer_matches_risk_free_even_without_payload():
    """B1 layer 1: the over-generic 'rate' keyword is gone; keyword inference
    alone must not attribute risk_free from savings_rate text."""
    checks = [
        _unknown_check("1", "Earnings vs savings", {"earnings_growth": None, "savings_rate": 0.02}),
    ]
    fields = {r["field"] for r in classify_missing_inputs(checks)}
    assert "risk_free_rate_10y_5y_avg" not in fields


def test_genuinely_missing_rate_is_detected_via_fair_value_root_cause():
    """B1 layer 2: with the payload proving the rate absent, the UNKNOWN
    fair-value checks are attributed to it explicitly (root cause), and the
    attribution lists those checks."""
    checks = [
        _unknown_check("1", "Below fair value", {"price": 100.0, "fair_value": None, "factor": 1.0}),
        _unknown_check("2", "Significantly below fair value", {"price": 100.0, "fair_value": None, "factor": 0.8}),
        _unknown_check("3", "PE vs benchmark", {"pe": 30.0, "benchmark": None}, reason_code="PROVIDER_LIMITATION"),
    ]
    records = classify_missing_inputs(checks, input_payload=_payload(with_rate=False))
    by_field = {r["field"]: r for r in records}
    assert "risk_free_rate_10y_5y_avg" in by_field
    rf = by_field["risk_free_rate_10y_5y_avg"]
    assert rf["criticality"] == "critical"
    assert rf["checks_affected_count"] == 2
    assert {c["check_id"] for c in rf["checks_affected"]} == {"1", "2"}
    # equity_risk_premium shares the same downstream signature
    assert "equity_risk_premium" in by_field


def test_rate_present_but_lineage_missing_still_counts_as_missing():
    """A value whose own lineage says source_quality=missing must not be
    treated as present — presence requires substance, not just a key."""
    checks = [
        _unknown_check("1", "Below fair value", {"price": 100.0, "fair_value": None, "factor": 1.0}),
    ]
    records = classify_missing_inputs(checks, input_payload=_payload(with_rate=True, lineage_quality="missing"))
    fields = {r["field"] for r in records}
    assert "risk_free_rate_10y_5y_avg" in fields


def test_no_payload_keeps_prior_keyword_behavior_for_named_fields():
    """Without a payload, explicit field naming in check text still works."""
    checks = [
        _unknown_check("7", "Discount rate check", {"risk_free_rate_10y_5y_avg": None}),
    ]
    fields = {r["field"] for r in classify_missing_inputs(checks)}
    assert "risk_free_rate_10y_5y_avg" in fields
