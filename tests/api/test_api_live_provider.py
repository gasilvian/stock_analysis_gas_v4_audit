from sws_engine.data.recorded_fixtures import load_recorded_snapshot
from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload
from sws_engine.providers.live_errors import YFinanceDependencyError


class MockProvider:
    def __init__(self, refresh=False):
        self.refresh = refresh

    def build_payload(self, ticker, valuation_date=None, market=None, industry=None, overrides=None):
        return map_yfinance_snapshot_to_input_payload(
            load_recorded_snapshot("AAPL"), valuation_date=valuation_date, market=market, industry=industry, overrides=overrides)


def test_build_payload_yfinance_endpoint_with_mock_provider(api_client, monkeypatch):
    import sws_engine.api.routes_live as routes_live
    monkeypatch.setattr(routes_live, "_provider", lambda refresh=False: MockProvider(refresh=refresh))
    r = api_client.post("/providers/yfinance/build-payload", json={
        "ticker": "AAPL", "valuation_date": "2026-07-08", "market": "US", "industry": "Technology"})
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["provider_profile"] == "yfinance_pragmatic"
    assert body["input_payload"]["ticker"] == "AAPL"
    assert body["warnings"]


def test_company_live_endpoint_with_mock_provider(api_client, monkeypatch):
    import sws_engine.api.routes_live as routes_live
    monkeypatch.setattr(routes_live, "_provider", lambda refresh=False: MockProvider(refresh=refresh))
    r = api_client.post("/analyze/company-live", json={
        "ticker": "AAPL", "valuation_date": "2026-07-08", "market": "US", "industry": "Technology", "persist": False})
    assert r.status_code == 200
    body = r.json()
    assert body["output"]["ticker"] == "AAPL"
    assert len(body["output"]["checks"]) == 30


def test_company_live_without_yfinance_dependency_returns_503(api_client, monkeypatch):
    import sws_engine.api.routes_live as routes_live

    class MissingProvider:
        def __init__(self, refresh=False):
            pass
        def build_payload(self, *args, **kwargs):
            raise YFinanceDependencyError('Install live extra: pip install -e ".[live]"')

    monkeypatch.setattr(routes_live, "_provider", lambda refresh=False: MissingProvider(refresh=refresh))
    r = api_client.post("/analyze/company-live", json={"ticker": "AAPL"})
    assert r.status_code == 503
