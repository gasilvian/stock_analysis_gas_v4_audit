import os
import pytest


@pytest.mark.live
def test_yfinance_live_optional_aapl_payload():
    if os.getenv("SWS_RUN_LIVE_TESTS") != "1":
        pytest.skip("live yfinance tests are opt-in via SWS_RUN_LIVE_TESTS=1")
    from sws_engine.providers.yfinance_live import YFinanceLiveProvider
    provider = YFinanceLiveProvider(refresh=True)
    payload = provider.build_payload("AAPL", market="US", industry="Technology")
    assert payload["ticker"] == "AAPL"
    assert payload["provider_profile"] == "yfinance_pragmatic"
