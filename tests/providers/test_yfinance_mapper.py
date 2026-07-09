import json

from sws_engine.data.recorded_fixtures import load_recorded_snapshot
from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload


def _payload():
    return map_yfinance_snapshot_to_input_payload(
        load_recorded_snapshot("AAPL"), valuation_date="2026-07-08", market="US", industry="Technology")


def test_map_price_from_history():
    p = _payload()
    assert p["price"] == 210.0
    assert p["lineage"]["price_as_of"] == "2026-07-08"
    assert p["lineage"]["field_lineage"]["price"]["source_quality"] == "exact"


def test_map_financials_latest_period_lineage():
    p = _payload()
    assert p["total_assets"] == 352000000000.0
    assert p["lineage"]["financials_as_of"] == "2025-09-30"
    assert p["lineage"]["field_lineage"]["total_assets"]["provider"] == "yfinance"


def test_missing_intangible_assets_prevents_exact_pb():
    p = _payload()
    assert p.get("intangible_assets") is None
    meta = p["lineage"]["field_lineage"]["intangible_assets"]
    assert meta["source_quality"] == "missing"
    assert any("tangible PB cannot be exact" in w for w in p["builder_warnings"])


def test_dividends_aggregate_to_dps_history():
    p = _payload()
    assert len(p["dps_history_10y"]) == 10
    assert p["dps_history_10y"][0] > 0
    assert p["lineage"]["field_lineage"]["dps_history_10y"]["transform"] == "calendar_year_sum_not_padded"


def test_sub_10y_dividend_history_not_padded():
    raw = load_recorded_snapshot("AAPL")
    raw["dividends"] = {"2024-01-01": 1.0, "2025-01-01": 1.1}
    p = map_yfinance_snapshot_to_input_payload(raw, valuation_date="2026-07-08")
    assert p["dps_history_10y"] == [1.0, 1.1]
    assert any("fewer than 10" in w for w in p["builder_warnings"])


def test_adjusted_fcf_from_ocf_minus_avg_capex_inputs():
    p = _payload()
    assert p["operating_cash_flow"] == 118000000000.0
    assert p["capex_history_3y"] == [11000000000.0, 9800000000.0, 12300000000.0]


def test_missing_analyst_estimates_provider_limitation():
    p = _payload()
    assert any("analyst_estimates_weighted" in w for w in p["builder_warnings"])
    assert p["lineage"]["field_lineage"]["analyst_estimates_weighted"]["source_quality"] == "missing"


def test_missing_fcf_estimates_provider_limitation():
    p = _payload()
    assert any("fcf_estimates" in w for w in p["builder_warnings"])
    assert p["lineage"]["field_lineage"]["fcf_estimates"]["source_quality"] == "missing"


def test_bank_specific_fields_missing_provider_limitation():
    p = _payload()
    assert p["lineage"]["field_lineage"]["bank_deposits_npl_chargeoffs"]["source_quality"] == "missing"


def test_reit_affo_ffo_nav_missing_provider_limitation():
    p = _payload()
    assert p["lineage"]["field_lineage"]["affo_ffo_nav"]["source_quality"] == "missing"


def test_manual_overrides_apply_with_lineage():
    p = map_yfinance_snapshot_to_input_payload(load_recorded_snapshot("AAPL"), overrides={
        "fields": {"risk_free_rate_10y_5y_avg": {"value": 0.035, "source_quality": "assumption", "source_class": "E2"}}
    })
    assert p["risk_free_rate_10y_5y_avg"] == 0.035
    assert p["lineage"]["field_lineage"]["risk_free_rate_10y_5y_avg"]["provider"] == "manual_override"
