
def test_post_analyze_portfolio_returns_output(api_client, demo_portfolio_payload):
    r = api_client.post("/analyze/portfolio", json={"input_payload": demo_portfolio_payload, "persist": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metadata"]["persisted"] is True
    assert body["metadata"]["run_id"]
    assert body["metadata"]["portfolio_id"]
    out = body["output"]
    assert "snowflake" in out
    assert "returns_per_position" in out


def test_get_portfolio_latest_and_history(api_client, demo_portfolio_payload):
    r = api_client.post("/analyze/portfolio", json={"input_payload": demo_portfolio_payload, "persist": True})
    assert r.status_code == 200, r.text
    pid = r.json()["metadata"]["portfolio_id"]
    latest = api_client.get(f"/portfolios/{pid}/latest")
    assert latest.status_code == 200, latest.text
    hist = api_client.get(f"/portfolios/{pid}/history")
    assert hist.status_code == 200, hist.text
    assert hist.json()["points"]
