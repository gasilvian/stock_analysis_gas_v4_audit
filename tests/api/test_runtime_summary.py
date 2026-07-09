def test_runtime_summary_reports_persisted_runs(api_client, demo_company_payload):
    r = api_client.post("/analyze/company",
                        json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    rs = api_client.get("/meta/runtime-summary")
    assert rs.status_code == 200, rs.text
    body = rs.json()
    assert body["company_runs_count"] >= 1
    assert body["latest_run_at"]
    assert demo_company_payload["ticker"] in body["tickers_available"]
    assert "production-readiness" in body["production_readiness_hint"]
    assert body["db_path"]


def test_runtime_summary_empty_db(api_client):
    rs = api_client.get("/meta/runtime-summary")
    assert rs.status_code == 200, rs.text
    body = rs.json()
    assert body["company_runs_count"] >= 0
    assert isinstance(body["tickers_available"], list)
