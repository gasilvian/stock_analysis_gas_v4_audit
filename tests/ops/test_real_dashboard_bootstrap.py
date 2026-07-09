"""Offline tests for the real-dashboard-bootstrap workflow.

No network: the provider factory is monkeypatched to a recorded-fixture
provider, matching the pattern used by tests/api/test_api_live_provider.py.
"""
import json
import os

import pytest

from sws_engine.data.recorded_fixtures import load_recorded_snapshot
from sws_engine.ops import real_dashboard_bootstrap as rdb
from sws_engine.providers.live_errors import LiveProviderError
from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = lambda *p: os.path.join(ROOT, *p)  # noqa: E731


class MockProvider:
    """Recorded-fixture provider; FAILME simulates a live failure."""

    def __init__(self, refresh=False):
        self.refresh = refresh

    def build_payload(self, ticker, valuation_date=None, market=None,
                      industry=None, overrides=None):
        if ticker == "FAILME":
            raise LiveProviderError("simulated fetch failure")
        payload = map_yfinance_snapshot_to_input_payload(
            load_recorded_snapshot("AAPL"), valuation_date=valuation_date,
            market=market, industry=industry, overrides=overrides)
        payload["ticker"] = ticker
        return payload


def _run(tmp_path, monkeypatch, tickers, **kw):
    monkeypatch.setattr(rdb, "_provider", lambda refresh=False: MockProvider(refresh))
    return rdb.run_real_dashboard_bootstrap(
        tickers=tickers,
        market="US",
        valuation_date="auto",
        db_path=str(tmp_path / "sws.db"),
        persist=True,
        output_dir=str(tmp_path / "boot"),
        assumptions_path=D("config", "assumptions.yaml"),
        schema_path=D("schemas", "output_schema.json"),
        bond_csv=str(tmp_path / "missing_bond.csv"),
        erp_json=str(tmp_path / "missing_erp.json"),
        **kw)


def test_bootstrap_persists_success_and_isolates_failure(tmp_path, monkeypatch):
    summary = _run(tmp_path, monkeypatch, ["AAPL", "FAILME"])
    # failed ticker does not stop the batch
    assert summary["tickers_succeeded"] == ["AAPL"]
    assert summary["tickers_failed"][0]["ticker"] == "FAILME"
    assert summary["status"] == "PASS_WITH_LIMITATIONS"
    assert summary["persisted_count"] == 1
    # summary + report files exist
    assert os.path.exists(summary["summary_path"])
    assert os.path.exists(summary["report_path"])
    # persisted output is retrievable from the DB
    from sws_engine.api.db_adapter import ApiDbAdapter
    db = ApiDbAdapter(str(tmp_path / "sws.db"), D("config", "assumptions.yaml"))
    latest = db.get_latest_company("AAPL")
    db.close()
    assert latest is not None
    assert latest["ticker"] == "AAPL"
    assert len([c for c in latest["checks"] if c["axis"] != "management"]) == 30


def test_bootstrap_missing_rates_and_erp_do_not_crash(tmp_path, monkeypatch):
    summary = _run(tmp_path, monkeypatch, ["AAPL"])
    joined = " ".join(summary["global_warnings"])
    assert "MISSING_CURATED_RATE_SOURCE" in joined
    assert "MISSING_CURATED_ERP_SOURCE" in joined
    assert summary["status"] == "PASS_WITH_LIMITATIONS"


def test_bootstrap_no_fake_values_and_unknown_preserved(tmp_path, monkeypatch):
    summary = _run(tmp_path, monkeypatch, ["AAPL"])
    out_path = os.path.join(summary["output_dir"], "AAPL_output.json")
    with open(out_path, "r", encoding="utf-8") as fh:
        output = json.load(fh)
    # score_normalized is never computed
    assert "score_normalized" not in json.dumps(output)
    # provider degradation stays visible
    assert output["provider_profile"] == "yfinance_pragmatic"
    assert output.get("warnings")
    # the bootstrap layer adds no analytical values: the payload it saved
    # equals the mapper payload for the same fixture, byte-for-byte
    with open(os.path.join(summary["output_dir"], "AAPL_payload.json"), "r",
              encoding="utf-8") as fh:
        saved_payload = json.load(fh)
    expected = map_yfinance_snapshot_to_input_payload(
        load_recorded_snapshot("AAPL"), valuation_date=None, market="US",
        industry=None, overrides=None)
    expected["ticker"] = "AAPL"
    assert saved_payload == expected


def test_bootstrap_fails_below_min_success_count(tmp_path, monkeypatch):
    summary = _run(tmp_path, monkeypatch, ["FAILME"], min_success_count=1)
    assert summary["status"] == "FAIL"
    assert summary["tickers_succeeded"] == []


def test_bootstrap_requires_tickers_or_watchlist():
    with pytest.raises(ValueError):
        rdb.run_real_dashboard_bootstrap(tickers=None, watchlist_path=None)


def test_bootstrap_reads_watchlist(tmp_path, monkeypatch):
    wl = tmp_path / "watchlist.csv"
    wl.write_text("ticker\nAAPL\n", encoding="utf-8")
    summary = _run(tmp_path, monkeypatch, None, watchlist_path=str(wl))
    assert summary["tickers_requested"] == ["AAPL"]
