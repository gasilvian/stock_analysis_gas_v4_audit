from fastapi.testclient import TestClient

from sws_engine.api.app import app


def test_root_ok(api_client):
    r = api_client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/meta/health"


def test_meta_health_ok(api_client):
    r = api_client.get("/meta/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data_layer"] == "synthetic/no-network"
    assert body["live_market_data"] is False
    assert body["dashboard_available"] is False


def test_openapi_schema_available(api_client):
    r = api_client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for path in ("/analyze/company", "/analyze/portfolio", "/meta/health", "/screener"):
        assert path in paths


def test_api_key_required_when_enabled(monkeypatch, api_paths):
    monkeypatch.setenv("SWS_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("SWS_API_KEY", "secret")
    c = TestClient(app)
    r = c.get("/meta/health")
    assert r.status_code == 401
    r2 = c.get("/meta/health", headers={"X-API-Key": "secret"})
    assert r2.status_code == 200
