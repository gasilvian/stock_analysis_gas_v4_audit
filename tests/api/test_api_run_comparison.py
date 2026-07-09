import json
from pathlib import Path

from fastapi.testclient import TestClient

from sws_engine.api.app import app

FIX = Path("tests/fixtures/run_comparison")


def test_api_compare_runs_endpoint():
    client = TestClient(app)
    payload = {
        "previous": json.loads((FIX / "AAPL_previous_audit_summary.json").read_text(encoding="utf-8")),
        "current": json.loads((FIX / "AAPL_current_audit_summary.json").read_text(encoding="utf-8")),
        "comparison_id": "api-aapl-p12",
    }
    resp = client.post("/research/compare-runs", json=payload)
    assert resp.status_code == 200, resp.text
    package = resp.json()["run_comparison"]
    assert package["ticker"] == "AAPL"
    assert package["comparison_id"] == "api-aapl-p12"
    assert package["unknown_changes"]["current_unknown_checks_count"] == 5
    assert package["recommendation_language_absent"] is True
