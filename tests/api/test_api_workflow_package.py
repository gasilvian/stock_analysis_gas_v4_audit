import json
from pathlib import Path

from fastapi.testclient import TestClient

from sws_engine.api.app import app

FIX = Path("tests/fixtures/workflow_package")


def test_api_workflow_package_endpoint():
    client = TestClient(app)
    payload = {
        "audit_summary": json.loads((FIX / "AAPL_audit_summary.json").read_text(encoding="utf-8")),
        "sensitivity_summary": json.loads((FIX / "AAPL_sensitivity_summary.json").read_text(encoding="utf-8")),
        "business_risk": json.loads((FIX / "AAPL_business_risk_package.json").read_text(encoding="utf-8")),
        "workflow_id": "api-p13-aapl",
    }
    resp = client.post("/research/workflow-package", json=payload)
    assert resp.status_code == 200, resp.text
    package = resp.json()["workflow_package"]
    assert package["schema_version"] == "workflow_package.v0.1"
    assert package["workflow_id"] == "api-p13-aapl"
    assert package["api_wiring"]["audit_summary"]["path"] == "/companies/AAPL/audit"
    assert package["not_investment_advice"] is True
