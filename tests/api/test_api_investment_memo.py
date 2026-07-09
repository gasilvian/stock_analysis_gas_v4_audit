import json
from pathlib import Path

from fastapi.testclient import TestClient

from sws_engine.api.app import app

FIX = Path("tests/fixtures/investment_memo")


def test_api_generate_investment_memo_endpoint():
    client = TestClient(app)
    payload = {
        "audit_summary": json.loads((FIX / "AAPL_audit_summary.json").read_text(encoding="utf-8")),
        "sensitivity_summary": json.loads((FIX / "AAPL_sensitivity_summary.json").read_text(encoding="utf-8")),
        "business_risk": json.loads((FIX / "AAPL_business_risk_package.json").read_text(encoding="utf-8")),
        "thesis_status": json.loads((FIX / "AAPL_thesis_status.json").read_text(encoding="utf-8")),
        "portfolio_audit": json.loads((FIX / "core_portfolio_audit.json").read_text(encoding="utf-8")),
    }
    resp = client.post("/research/memo", json=payload)
    assert resp.status_code == 200, resp.text
    memo = resp.json()["investment_memo"]
    assert memo["ticker"] == "AAPL"
    assert memo["recommendation_language_absent"] is True
    assert memo["unknown_summary"]["unknown_checks_count"] == 5
