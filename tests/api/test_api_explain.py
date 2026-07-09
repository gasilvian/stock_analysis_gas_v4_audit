def test_company_explain_endpoint(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    ticker = demo_company_payload["ticker"]
    exp = api_client.get(f"/companies/{ticker}/explain?mode=plain_english")
    assert exp.status_code == 200, exp.text
    body = exp.json()
    assert body["metadata"]["run_id"]
    package = body["explanations"]
    assert package["ticker"] == ticker
    assert package["mode"] == "plain_english"
    assert package["not_investment_advice"] is True
    assert "check_explanations" in package


def test_company_explain_rejects_bad_mode(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    ticker = demo_company_payload["ticker"]
    exp = api_client.get(f"/companies/{ticker}/explain?mode=free_text_llm")
    assert exp.status_code == 400
