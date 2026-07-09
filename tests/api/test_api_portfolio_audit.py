from fastapi.testclient import TestClient

from sws_engine.api.app import app


def test_api_portfolio_audit_endpoint():
    client = TestClient(app)
    payload = {
        "portfolio_id": "api_core",
        "holdings": [
            {"ticker": "AAPL", "weight": 0.7, "sector": "Technology", "factor": "Quality", "macro_exposure": ["rates"]},
            {"ticker": "JPM", "weight": 0.3, "sector": "Financials", "factor": "Value", "macro_exposure": ["rates", "credit"]},
        ],
        "audit_summaries": {
            "AAPL": {"ticker": "AAPL", "schema_version": "audit_summary.v0.2", "data_confidence": {"level": "HIGH"}, "model_applicability": {"status": "STANDARD_OK", "allowed_score_usage": "rankable"}, "conclusion_risk": {"risk_level": "LOW"}, "source_quality": "HIGH", "source_class": "official_filing"},
            "JPM": {"ticker": "JPM", "schema_version": "audit_summary.v0.2", "data_confidence": {"level": "MEDIUM"}, "model_applicability": {"status": "DEGRADED", "allowed_score_usage": "do_not_compare"}, "conclusion_risk": {"risk_level": "HIGH"}, "source_quality": "MEDIUM", "source_class": "official_filing"},
        },
    }
    resp = client.post("/audit/portfolio", json=payload)
    assert resp.status_code == 200, resp.text
    package = resp.json()["portfolio_audit"]
    assert package["portfolio_id"] == "api_core"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["weighted_conclusion_risk"]["level"] == "MEDIUM"
    assert package["unknown_exposure"]["weight_pct"] == 0.0
