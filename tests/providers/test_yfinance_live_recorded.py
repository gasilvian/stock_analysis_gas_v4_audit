from sws_engine.data.recorded_fixtures import load_recorded_snapshot
from sws_engine.orchestration.company_run import run_company_analysis
from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload


def test_build_payload_from_recorded_aapl_snapshot():
    payload = map_yfinance_snapshot_to_input_payload(load_recorded_snapshot("AAPL"), valuation_date="2026-07-08")
    assert payload["ticker"] == "AAPL"
    assert payload["provider_profile"] == "yfinance_pragmatic"


def test_run_company_analysis_from_recorded_payload_schema_valid():
    payload = map_yfinance_snapshot_to_input_payload(load_recorded_snapshot("AAPL"), valuation_date="2026-07-08")
    out = run_company_analysis(payload, "config/assumptions.yaml", "schemas/output_schema.json")
    assert out["ticker"] == "AAPL"
    assert len(out["checks"]) == 30


def test_recorded_snapshot_has_provider_versions():
    payload = map_yfinance_snapshot_to_input_payload(load_recorded_snapshot("AAPL"), valuation_date="2026-07-08")
    assert "yfinance" in payload["lineage"]["provider_versions"]
