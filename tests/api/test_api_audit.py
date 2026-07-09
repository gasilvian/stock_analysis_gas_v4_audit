def test_company_audit_endpoint(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    ticker = demo_company_payload["ticker"]
    audit = api_client.get(f"/companies/{ticker}/audit")
    assert audit.status_code == 200, audit.text
    body = audit.json()
    assert body["metadata"]["run_id"]
    assert body["audit"]["ticker"] == ticker
    assert body["audit"]["data_confidence"]["level"] in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    assert body["audit"]["model_applicability"]["status"] in {"STANDARD_OK", "DEGRADED", "NOT_APPLICABLE", "UNKNOWN"}
    assert body["audit"]["not_investment_advice"] is True


def test_company_audit_component_endpoints(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    ticker = demo_company_payload["ticker"]

    dc = api_client.get(f"/companies/{ticker}/data-confidence")
    assert dc.status_code == 200, dc.text
    assert dc.json()["data_confidence"]["confidence_grade"] in {"A", "B", "C", "D", "E", "UNKNOWN"}
    assert "source_tier_mix" in dc.json()["data_confidence"]

    ma = api_client.get(f"/companies/{ticker}/model-applicability")
    assert ma.status_code == 200, ma.text
    assert ma.json()["model_applicability"]["allowed_score_usage"] in {"rankable", "display_only", "audit_only", "do_not_compare"}
