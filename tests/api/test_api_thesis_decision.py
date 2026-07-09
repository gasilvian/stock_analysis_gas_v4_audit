from fastapi.testclient import TestClient

from sws_engine.api.app import app


def test_api_thesis_evaluate_endpoint():
    client = TestClient(app)
    payload = {
        "thesis": {
            "ticker": "AAPL",
            "watch_metrics": [
                {"id": "risk_not_high", "source_field": "conclusion_risk.risk_level", "operator": "in", "threshold": ["HIGH", "UNKNOWN"]}
            ],
            "invalidation_rules": [
                {"id": "rankable_required", "source_field": "model_applicability.allowed_score_usage", "operator": "neq", "threshold": "rankable"}
            ],
        },
        "audit_summary": {
            "ticker": "AAPL",
            "data_confidence": {"level": "HIGH"},
            "model_applicability": {"allowed_score_usage": "rankable"},
            "conclusion_risk": {"risk_level": "LOW"},
            "not_investment_advice": True,
        },
    }
    resp = client.post("/research/thesis/evaluate", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()["thesis_status"]
    assert body["ticker"] == "AAPL"
    assert body["thesis_status"] == "ON_TRACK"


def test_api_decision_journal_endpoint():
    client = TestClient(app)
    payload = {
        "decision": {"ticker": "AAPL", "decision_type": "research_deeper", "expected_outcome": "Manual research."},
        "audit_summary": {"ticker": "AAPL", "data_confidence": {"level": "HIGH"}, "conclusion_risk": {"risk_level": "LOW"}},
        "thesis_status": {"ticker": "AAPL", "thesis_status": "ON_TRACK"},
    }
    resp = client.post("/research/decision", json=payload)
    assert resp.status_code == 200, resp.text
    record = resp.json()["decision_record"]
    assert record["status"] == "PASS"
    assert record["decision_type"] == "research_deeper"
    assert record["thesis_status_at_decision"] == "ON_TRACK"

    bad = client.post("/research/decision", json={"decision": {"ticker": "AAPL", "decision_type": "buy"}})
    assert bad.status_code == 200
    assert bad.json()["decision_record"]["reason_code"] == "DECISION_TYPE_NOT_ALLOWED"
