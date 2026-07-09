from fastapi.testclient import TestClient

from sws_engine.api.app import app


def test_api_watchlist_audit_endpoint():
    client = TestClient(app)
    payload = {
        "watchlist": [
            {"ticker": "AAPL", "idea_source": "manual", "priority": "high"},
            {"ticker": "MISS", "idea_source": "manual", "priority": "low"},
        ],
        "audit_summaries": {
            "AAPL": {
                "schema_version": "audit_summary.v0.2",
                "ticker": "AAPL",
                "exchange": "NasdaqGS",
                "valuation_date": "2026-07-09",
                "provider_profile": "sws_public_faithful_manual_inputs",
                "data_confidence": {"level": "HIGH", "confidence_grade": "A", "unknown_checks_count": 0, "critical_missing_inputs": []},
                "model_applicability": {"status": "STANDARD_OK", "allowed_score_usage": "rankable", "company_type_detected": "standard_industrial"},
                "conclusion_risk": {"risk_level": "LOW"},
                "critical_missing_inputs": [],
                "provider_degradation_visible": False,
                "not_investment_advice": True,
            }
        },
    }
    resp = client.post("/audit/watchlist", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()["watchlist_audit"]
    assert body["watchlist_size"] == 2
    assert body["bucket_counts"]["Researchable Now"] == 1
    assert body["unknown_artifact_count"] == 1
