import json

import jsonschema


def test_post_analyze_company_returns_schema_valid_output(api_client, demo_company_payload, schema_path):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metadata"]["persisted"] is False
    output = body["output"]
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    jsonschema.validate(output, schema)
    assert output["ticker"] == "DEMO"
    assert len([c for c in output["checks"] if c["axis"] != "management"]) == 30
    assert "scores" in output and "lineage" in output and "warnings" in output


def test_post_analyze_company_persist_true_writes_db(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metadata"]["persisted"] is True
    assert body["metadata"]["run_id"]


def test_get_company_latest_after_persist(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    latest = api_client.get("/companies/DEMO/latest")
    assert latest.status_code == 200, latest.text
    assert latest.json()["output"]["ticker"] == "DEMO"


def test_invalid_company_payload_returns_422_or_400(api_client):
    r = api_client.post("/analyze/company", json={"input_payload": {"ticker": "BAD"}, "persist": False})
    assert r.status_code in (400, 422), r.text


def test_api_does_not_hide_unknown_or_warnings(api_client, yfinance_degraded_payload):
    r = api_client.post("/analyze/company", json={"input_payload": yfinance_degraded_payload, "persist": False})
    assert r.status_code == 200, r.text
    output = r.json()["output"]
    assert output["warnings"]
    assert any("PROVIDER_LIMITATION" in w for w in output["warnings"])
    assert any(c["result"] == "UNKNOWN" for c in output["checks"])
