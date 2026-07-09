import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from sws_engine.api.app import app
from sws_engine.api.db_adapter import ApiDbAdapter


def _demo_output():
    out = json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))
    out["ticker"] = "RISK"
    return out


def test_api_business_risks_endpoint(tmp_path, monkeypatch):
    db_path = tmp_path / "sws.db"
    adapter = ApiDbAdapter(str(db_path), "config/assumptions.yaml")
    payload = json.loads(Path("tests/fixtures/business_risk/risk_payload.json").read_text(encoding="utf-8"))
    adapter.save_company_output(_demo_output(), payload)
    adapter.close()

    monkeypatch.setenv("SWS_DB_PATH", str(db_path))
    client = TestClient(app)
    resp = client.get("/companies/RISK/business-risks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["business_risks"]["ticker"] == "RISK"
    assert body["business_risks"]["red_flags_summary"]["fail_count"] >= 4
