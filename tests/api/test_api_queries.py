
def test_get_company_history_returns_score_and_coverage(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    hist = api_client.get("/companies/DEMO/history?axis=health")
    assert hist.status_code == 200, hist.text
    points = hist.json()["points"]
    assert points
    assert all("score_raw" in p and "coverage_pct" in p for p in points)


def test_get_company_checks_filter_unknown(api_client, yfinance_degraded_payload):
    r = api_client.post("/analyze/company", json={"input_payload": yfinance_degraded_payload, "persist": True})
    assert r.status_code == 200, r.text
    chk = api_client.get("/companies/DEGRADED/checks?result=UNKNOWN")
    assert chk.status_code == 200, chk.text
    checks = chk.json()["checks"]
    assert checks
    assert all(c["result"] == "UNKNOWN" for c in checks)


def test_screener_returns_coverage(api_client, demo_company_payload):
    r = api_client.post("/analyze/company", json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    screen = api_client.get("/screener?axis=value&min_score=0&min_coverage=0")
    assert screen.status_code == 200, screen.text
    rows = screen.json()["rows"]
    assert rows
    assert all("coverage_pct" in row["scores"]["value"] for row in rows)
    default_screen = api_client.get("/screener?axis=value&min_score=0")
    assert default_screen.status_code == 200
    default_rows = default_screen.json()["rows"]
    assert all(row["scores"]["value"]["coverage_pct"] >= 0.66 for row in default_rows)


def test_missing_ticker_latest_returns_404(api_client):
    r = api_client.get("/companies/NO_SUCH_TICKER/latest")
    assert r.status_code == 404
