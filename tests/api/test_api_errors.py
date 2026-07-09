
def test_assumptions_current_returns_hash(api_client):
    r = api_client.get("/assumptions/current")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assumptions_hash"]
    assert "unknown_scoring_policy" in body


def test_averages_snapshot_missing_returns_404(api_client):
    r = api_client.get("/averages/NOPE/2099-01-01")
    assert r.status_code == 404
