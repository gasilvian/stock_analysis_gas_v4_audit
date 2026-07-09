def test_companies_list_shows_persisted_ticker(api_client, demo_company_payload):
    r = api_client.post("/analyze/company",
                        json={"input_payload": demo_company_payload, "persist": True})
    assert r.status_code == 200, r.text
    lst = api_client.get("/companies")
    assert lst.status_code == 200, lst.text
    tickers = lst.json()["tickers"]
    assert tickers
    row = next(t for t in tickers if t["ticker"] == demo_company_payload["ticker"])
    assert row["latest_valuation_date"]
    assert row["provider_profile"]
    # coverage is mandatory next to any score-adjacent listing
    assert set(row["coverage_summary"].keys()) == {
        "value", "future", "past", "health", "dividend"}
    assert "unknown_checks_count" in row
    assert "warnings_count" in row


def test_companies_list_empty_db(api_client):
    lst = api_client.get("/companies")
    assert lst.status_code == 200, lst.text
    assert isinstance(lst.json()["tickers"], list)
