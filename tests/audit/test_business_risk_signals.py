import json
from pathlib import Path

from jsonschema import validate

from sws_engine.audit.risk_signals import build_business_risk_package, business_risk_report_md


def _payload(name="risk_payload.json"):
    return json.loads(Path("tests/fixtures/business_risk" , name).read_text(encoding="utf-8"))


def test_business_risk_package_schema_and_red_flags():
    package = build_business_risk_package(_payload())
    schema = json.loads(Path("schemas/aux/business_risk_package.schema.json").read_text(encoding="utf-8"))
    validate(package, schema)

    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["red_flags_summary"]["fail_count"] >= 4
    flag_ids = {f["flag_id"] for f in package["red_flags"]}
    assert "DIVIDEND_NOT_COVERED_BY_FCF" in flag_ids
    assert "HIGH_INTANGIBLES_TO_ASSETS" in flag_ids
    assert "ELEVATED_NET_DEBT_TO_EQUITY" in flag_ids
    assert "SHARE_DILUTION_ABOVE_10PCT" in flag_ids
    assert package["not_investment_advice"] is True


def test_accounting_quality_and_capital_allocation_are_deterministic():
    package = build_business_risk_package(_payload())
    assert package["accounting_quality"]["grade"] in {"WATCH", "WEAK", "NORMAL", "STRONG"}
    assert package["capital_allocation"]["assessment"] == "WATCH"
    assert any(item["reason_code"] == "CAPITAL_ALLOCATION_WATCH" for item in package["manual_review_items"])


def test_clean_payload_has_no_triggered_red_flags():
    package = build_business_risk_package(_payload("clean_payload.json"))
    assert package["red_flags_summary"]["fail_count"] == 0
    assert package["accounting_quality"]["status"] in {"PASS", "PASS_WITH_LIMITATIONS"}
    assert package["capital_allocation"]["assessment"] in {"BALANCED", "WATCH"}


def test_missing_payload_keeps_unknown_visible():
    package = build_business_risk_package({"ticker": "MISS"})
    assert package["status"] == "UNKNOWN"
    assert package["red_flags_summary"]["unknown_count"] >= 1
    assert package["manual_review_items"]


def test_business_risk_report_has_footer_and_no_recommendation_language():
    md = business_risk_report_md(build_business_risk_package(_payload()))
    assert "Not investment advice" in md
    assert "Business Risk Signals" in md
    forbidden = {" BUY ", " SELL ", " HOLD "}
    assert not any(word in md for word in forbidden)
