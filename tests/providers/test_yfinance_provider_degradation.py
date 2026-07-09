from sws_engine.data.recorded_fixtures import load_recorded_snapshot
from sws_engine.orchestration.company_run import run_company_analysis
from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload


def _output():
    payload = map_yfinance_snapshot_to_input_payload(
        load_recorded_snapshot("AAPL"), valuation_date="2026-07-08", market="US", industry="Technology")
    return payload, run_company_analysis(payload, "config/assumptions.yaml", "schemas/output_schema.json")


def test_yfinance_payload_has_provider_profile_yfinance_pragmatic():
    payload, _ = _output()
    assert payload["provider_profile"] == "yfinance_pragmatic"


def test_provider_limitations_visible_in_warnings():
    _, out = _output()
    assert any("PROVIDER_LIMITATION" in w for w in out["warnings"])
    assert any("yfinance_pragmatic" in w for w in out["warnings"])


def test_missing_fields_become_unknown_in_engine_output():
    _, out = _output()
    assert any(c["result"] == "UNKNOWN" for c in out["checks"])
    assert out["scores"]["value"]["unknown_checks_count"] >= 1


def test_no_book_value_per_share_used_as_exact_pb():
    payload, out = _output()
    assert payload.get("bookValuePerShare") is None
    v6 = [c for c in out["checks"] if c["axis"] == "value" and c["id"] == 6][0]
    assert v6["result"] == "UNKNOWN"
