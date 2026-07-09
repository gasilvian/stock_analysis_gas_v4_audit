"""Phase 3 data-layer tests: capability matrix, recorded provider,
averages builder, rates, payload builder, cache. All on synthetic curated
data shipped in data/ (no network)."""
import json
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = lambda *p: os.path.join(ROOT, *p)


def test_capability_matrix_is_honest_about_missing():
    from sws_engine.providers.capability_matrix import (
        YFINANCE_CAPABILITY, missing_fields)
    hard_missing = missing_fields("yfinance_pragmatic")
    # SWS-critical forward/institution fields must never be 'exact' in yfinance
    for f in ("fcf_estimates", "roe_3y_estimate", "estimated_payout_3y",
              "affo_ffo_nav", "bank_deposits_npl_chargeoffs",
              "market_averages", "industry_averages"):
        assert f in hard_missing
    # intangibles must never be claimed exact (PB risk from risk_register)
    assert YFINANCE_CAPABILITY["intangible_assets"] != "exact"


def test_recorded_provider_maps_and_degrades():
    from sws_engine.providers.recorded import RecordedProvider
    pr = RecordedProvider(D("data", "recorded", "SYN-ACME.json")).prepare(
        {"valuation_date": "2026-07-06"})
    p = pr.payload
    assert p["ticker"] == "SYN-ACME" and p["price"] == 92.0
    assert len(p["dps_history_10y"]) == 10
    assert p["synthetic_data"] is True
    assert pr.field_quality["fcf_estimates"] == "missing"
    assert pr.field_quality["eps"] == "exact"
    assert pr.field_quality["intangible_assets"] == "approximation"
    assert any("SYNTHETIC_CURATED_DATA" in d for d in pr.degradations)


def test_averages_builder_metrics_and_exclusions():
    from sws_engine.averages.builder import build_averages, load_universe
    rows = load_universe(D("data", "universe", "universe_US-SYN.csv"))
    snap = build_averages(rows, as_of="2026-07-06", min_universe_count=5,
                          savings_rate=0.02, cpi=0.028)
    mk = snap["market"]
    # ETF/DR excluded from universe
    assert set(snap["meta"]["excluded_instruments"]) == {"SYN-ETF", "SYN-DR"}
    assert mk["universe_count"] == 11
    # profitable-only PE median: SYN-E (eps<0) excluded -> 10 PEs
    # sorted PEs: 16.67,16.67,17.33,20,23.90,25,29.17,30,30,32
    # even count -> mean of middle pair (23.90, 25) = 24.451...
    assert abs(mk["pe_median_profitable"] - (98/4.1 + 25.0) / 2) < 1e-9
    assert mk["pb_average"] is not None and mk["pb_excluded_no_tangible_bv"] == 0
    assert mk["savings_rate"] == 0.02 and mk["cpi"] == 0.028
    # percentiles are ordered
    assert mk["dividend_yield_p10"] <= mk["dividend_yield_p25"] \
        <= mk["dividend_yield_p75"]
    # Software has 8 >= 5 -> industry level; Utilities 3 < 5 -> market fallback
    assert snap["industries"]["Software"]["fallback_level"] == "industry"
    assert snap["industries"]["Utilities"]["fallback_level"] == "market"
    assert any("FALLBACK" in w for w in snap["warnings"])


def test_averages_pb_excludes_non_tangible():
    from sws_engine.averages.builder import build_averages
    rows = [
        {"ticker": "X", "kind": "stock", "industry": "I", "price": 10.0,
         "eps": 1.0, "shares_outstanding": 100.0, "total_assets": 1000.0,
         "intangible_assets": 100.0, "total_liabilities": 400.0,
         "market_cap": 1000.0, "net_income_growth": 0.1,
         "revenue_growth": 0.1, "eps_growth": 0.1, "roa": 0.05,
         "dividend_yield": 0.02},
        {"ticker": "Y", "kind": "stock", "industry": "I", "price": 10.0,
         "eps": 1.0, "shares_outstanding": 100.0, "total_assets": None,
         "intangible_assets": None, "total_liabilities": None,
         "market_cap": 1000.0, "net_income_growth": 0.1,
         "revenue_growth": 0.1, "eps_growth": 0.1, "roa": 0.05,
         "dividend_yield": 0.02},
    ]
    snap = build_averages(rows, as_of="2026-07-06", min_universe_count=1)
    # Y cannot produce tangible PB -> excluded, never approximated
    assert snap["market"]["pb_excluded_no_tangible_bv"] == 1
    assert abs(snap["market"]["pb_average"] - 10.0 / 5.0) < 1e-9


def test_rates_bond_5y_average_and_erp_and_fx():
    from sws_engine.rates.rates import bond_10y_5y_average, fx_rate, load_erp
    rf = bond_10y_5y_average(D("data", "rates", "bond_yields_10y.csv"),
                             "US", "2026-07-06")
    # obs in window (2021-07-06..2026-07-06): 2021-12..2026-06 -> 6 values
    assert rf["observations"] == 6
    assert abs(rf["value"] - (0.0151 + 0.0388 + 0.0388 + 0.0430 + 0.0405
                              + 0.0398) / 6) < 1e-9
    erp = load_erp(D("data", "rates", "erp.json"), "RO")
    assert erp["value"] == 0.078
    fx = fx_rate(D("data", "fx", "fx_eod.csv"), "USDRON", "2026-07-05")
    assert fx["rate"] == 4.4310 and fx["as_of"] == "2026-07-03"  # EOD <= date


def test_payload_builder_end_to_end_acme(run):
    from sws_engine.averages.builder import build_averages, load_universe
    from sws_engine.orchestration.payload_builder import build_company_payload
    averages = build_averages(
        load_universe(D("data", "universe", "universe_US-SYN.csv")),
        as_of="2026-07-06", min_universe_count=5,
        savings_rate=0.02, cpi=0.028)
    payload, pr = build_company_payload(
        snapshot_path=D("data", "recorded", "SYN-ACME.json"),
        averages_snapshot=averages, industry="Software", country="US",
        valuation_date="2026-07-06",
        bond_csv=D("data", "rates", "bond_yields_10y.csv"),
        erp_json=D("data", "rates", "erp.json"))
    out = run(payload)
    # adjusted-FCF valuation computed (base), price below FV
    assert out["valuation_model"] == "two_stage_fcf"
    assert out["valuation_variant"] == "base"
    assert out["fair_value"] > 0
    # averages injected: market-relative checks evaluable
    v3 = next(c for c in out["checks"] if c["axis"] == "value" and c["id"] == 3)
    assert v3["result"] in ("PASS", "FAIL")
    # synthetic + fallback + assumption warnings survive into final output
    assert any("SYNTHETIC_CURATED_DATA" in w for w in out["warnings"])
    assert any("FALLBACK" in w for w in out["warnings"])
    assert any("equity risk premium" in w for w in out["warnings"])
    assert out["lineage"]["industry_averages_as_of"] == "2026-07-06"


def test_payload_builder_loss_making_burn(run):
    from sws_engine.averages.builder import build_averages, load_universe
    from sws_engine.orchestration.payload_builder import build_company_payload
    averages = build_averages(
        load_universe(D("data", "universe", "universe_US-SYN.csv")),
        as_of="2026-07-06", min_universe_count=5,
        savings_rate=0.02, cpi=0.028)
    payload, pr = build_company_payload(
        snapshot_path=D("data", "recorded", "SYN-BURN.json"),
        averages_snapshot=averages, industry="Software", country="US",
        valuation_date="2026-07-06",
        bond_csv=D("data", "rates", "bond_yields_10y.csv"),
        erp_json=D("data", "rates", "erp.json"))
    # burn inputs derived mechanically from recorded FCF history
    assert abs(payload["annual_free_cash_burn"] - 390e6) < 1
    assert abs(payload["cash_burn_growth_3y"] - ((390 / 250) ** 0.5 - 1)) < 1e-6
    out = run(payload)
    h = {c["id"]: c for c in out["checks"] if c["axis"] == "health"}
    assert h[5]["name"] == "cash_covers_stable_burn_1y"
    assert h[5]["result"] == "PASS"          # 700M > 390M
    assert h[6]["name"] == "cash_covers_growing_burn_1y"
    assert h[6]["result"] == "PASS"          # 700M > 487M
    # strict mode: no fair value inventable for a cash-burning company
    assert out["fair_value"] is None
    assert out["valuation_variant"] == "unknown"


def test_disk_cache_ttl(tmp_path):
    from sws_engine.data.cache import DiskCache
    c = DiskCache(str(tmp_path))
    c.put("prices/SYN-ACME", {"price": 92.0})
    assert c.get("prices/SYN-ACME")["price"] == 92.0
    assert c.get("prices/SYN-ACME", ttl_days=1)["price"] == 92.0
    assert c.get("prices/SYN-ACME", ttl_days=0) is None  # expired
    assert c.get("nonexistent") is None
