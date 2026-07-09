from __future__ import annotations

import requests

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.config import DashboardSettings


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def test_get_meta_health(monkeypatch):
    calls = {}

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        calls["method"] = method
        calls["url"] = url
        return DummyResponse(payload={"status": "ok", "data_layer": "synthetic/no-network"})

    monkeypatch.setattr(requests, "request", fake_request)
    client = ApiClient(DashboardSettings(api_url="http://api"))
    assert client.get_meta_health()["status"] == "ok"
    assert calls["url"] == "http://api/meta/health"


def test_get_company_latest(monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *a, **k: DummyResponse(payload={"output": {"ticker": "DEMO"}}))
    client = ApiClient(DashboardSettings(api_url="http://api"))
    assert client.get_company_latest("DEMO")["output"]["ticker"] == "DEMO"


def test_screener_default_coverage(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        captured["params"] = kwargs.get("params", {})
        return DummyResponse(payload={"rows": []})

    monkeypatch.setattr(requests, "request", fake_request)
    client = ApiClient(DashboardSettings(api_url="http://api"))
    client.screener(axis="value")
    assert captured["params"]["min_coverage"] == 0.66


def test_api_key_header(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        captured["headers"] = headers
        return DummyResponse(payload={"status": "ok"})

    monkeypatch.setattr(requests, "request", fake_request)
    client = ApiClient(DashboardSettings(api_url="http://api", api_key="secret"))
    client.get_root()
    assert captured["headers"]["X-API-Key"] == "secret"


def test_404_returns_none(monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *a, **k: DummyResponse(status_code=404, payload={"detail": "missing"}))
    client = ApiClient(DashboardSettings(api_url="http://api"))
    assert client.get_company_latest("NOPE") is None


def test_api_down_is_sanitized(monkeypatch):
    def fake_request(*args, **kwargs):
        raise requests.ConnectionError("boom stack details")

    monkeypatch.setattr(requests, "request", fake_request)
    client = ApiClient(DashboardSettings(api_url="http://api"))
    try:
        client.get_meta_health()
    except ApiClientError as exc:
        assert "API unavailable" in str(exc)
        assert "boom" not in str(exc)
    else:
        raise AssertionError("ApiClientError was expected")


def test_p13_workflow_api_client_methods(monkeypatch):
    calls = []

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        calls.append((method, url, kwargs))
        return DummyResponse(payload={"workflow_package": {"ticker": "AAPL"}})

    monkeypatch.setattr(requests, "request", fake_request)
    client = ApiClient(DashboardSettings(api_url="http://api"))
    client.get_company_workflow("AAPL")
    client.build_workflow_package({"ticker": "AAPL"}, workflow_id="wf")
    assert calls[0][0] == "GET"
    assert calls[0][1] == "http://api/companies/AAPL/workflow"
    assert calls[1][0] == "POST"
    assert calls[1][1] == "http://api/research/workflow-package"
    assert calls[1][2]["json"]["workflow_id"] == "wf"


def test_p08_to_p12_api_client_workflow_methods_exist():
    for name in [
        "audit_watchlist",
        "audit_portfolio",
        "generate_memo",
        "compare_runs",
        "get_company_sensitivity",
        "get_company_explain",
        "get_company_business_risks",
    ]:
        assert hasattr(ApiClient, name)
