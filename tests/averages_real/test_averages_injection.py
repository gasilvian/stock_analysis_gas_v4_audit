"""B3 tests: curated averages injection + P1.4a earnings-history enablement.

Pins the two enrichment steps that collapse the UNKNOWN mass observed in the
2026-07-10 real calibration: curated market/industry averages reaching live
payloads (B3) and SEC annual earnings history enabling the growth resolver's
'historical' route and therefore base fair value (calibration item
'base valuation enablement').
"""
import copy
import json
from pathlib import Path

from sws_engine.averages.injection import apply_averages_snapshot

ROOT = Path(__file__).resolve().parents[2]


def _real_snapshot(extra_industry: str | None = None):
    snap = json.loads((ROOT / "data/averages/averages_US-SYN_2026-07-06.json").read_text(encoding="utf-8"))
    snap = copy.deepcopy(snap)
    snap["meta"]["source"] = "yfinance_universe_curated"
    if extra_industry:
        snap["industries"][extra_industry] = dict(snap["industries"]["Software"])
    return snap


def test_synthetic_snapshots_are_refused_without_touching_payload():
    snap = json.loads((ROOT / "data/averages/averages_US-SYN_2026-07-06.json").read_text(encoding="utf-8"))
    assert "synthetic" in snap["meta"]["source"]
    payload = {"ticker": "T1", "industry": "Software"}
    report = apply_averages_snapshot(payload, snap)
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SYNTHETIC_AVERAGES_REFUSED"
    assert "market_averages" not in payload
    assert "industry_averages" not in payload


def test_injection_applies_market_and_matched_industry_with_e2_lineage():
    payload = {"ticker": "T1", "industry": "Software"}
    report = apply_averages_snapshot(payload, _real_snapshot())
    assert report["reason_code"] == "AVERAGES_INJECTED"
    assert set(report["applied_fields"]) == {"market_averages", "industry_averages"}
    assert payload["market_averages"]["pe_median_profitable"] is not None
    lin = payload["lineage"]["field_lineage"]
    assert lin["market_averages"]["provider"] == "curated_averages"
    assert lin["market_averages"]["source_quality"] == "approximation"
    assert lin["industry_averages"]["source_class"] == "E2"
    assert payload["industry_averages_as_of"] == payload["lineage"]["field_lineage"]["market_averages"]["as_of"]


def test_industry_miss_injects_market_only_and_stays_honest():
    payload = {"ticker": "AAPL", "industry": "Consumer Electronics"}
    report = apply_averages_snapshot(payload, _real_snapshot())
    assert report["applied_fields"] == ["market_averages"]
    assert payload.get("industry_averages") is None
    assert report["industry_matched"] is None
    assert any(w.startswith("INDUSTRY_AVERAGES_NOT_FOUND") for w in payload["builder_warnings"])


def test_existing_operator_values_are_preserved():
    payload = {"ticker": "T1", "industry": "Software",
               "industry_averages": {"pe_median_profitable": 99.0}}
    report = apply_averages_snapshot(payload, _real_snapshot())
    assert "industry_averages" in report["skipped_existing"]
    assert payload["industry_averages"]["pe_median_profitable"] == 99.0


def test_sec_earnings_history_enables_historical_growth_and_fair_value():
    """P1.4a end-to-end: recorded AAPL yfinance payload + curated rates + SEC
    snapshot (with the multi-year NetIncomeLoss fixture) must produce a
    non-null fair value via the ADJUSTED_FCF + historical growth route."""
    from sws_engine.orchestration.company_run import run_company_analysis
    from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload
    from sws_engine.rates.injection import build_curated_rates_overrides
    from sws_engine.sec.cik_resolver import resolve_cik
    from sws_engine.sec.companyfacts_adapter import get_companyfacts
    from sws_engine.sec.payload_merge import apply_sec_payload_updates
    from sws_engine.sec.statement_snapshot import build_statement_snapshot

    raw = json.loads((ROOT / "data/recorded_yfinance/AAPL_snapshot.json").read_text(encoding="utf-8"))
    inj = build_curated_rates_overrides(
        str(ROOT / "data/real_sources/rates/bond_yields_10y_curated.csv"),
        str(ROOT / "data/real_sources/rates/erp_curated.json"),
        country="US", valuation_date="2026-07-10")
    payload = map_yfinance_snapshot_to_input_payload(
        raw, valuation_date="2026-07-10", market="US", overrides=inj["overrides"])

    rec = resolve_cik("AAPL", ROOT / "tests/fixtures/sec/company_tickers.json")
    facts, src = get_companyfacts(rec.cik10, fixture_dir=ROOT / "tests/fixtures/sec/companyfacts", live=False)
    snap = build_statement_snapshot(facts, cik_record=rec, source_path=src, valuation_date="2026-07-10")

    history = snap["payload_updates"].get("earnings_history")
    assert history and len(history) == 5, "fixture carries FY2020-FY2024 NetIncomeLoss"
    assert history[0] == 57411000000.0 and history[-1] == 93736000000.0  # oldest -> newest
    lin = snap["payload_updates"]["lineage"]["field_lineage"]["earnings_history"]
    assert lin["source_quality"] == "exact" and lin["source_class"] == "E0"

    apply_sec_payload_updates(payload, snap["payload_updates"])
    output = run_company_analysis(payload, str(ROOT / "config/assumptions.yaml"), str(ROOT / "schemas/output_schema.json"))
    assert output.get("fair_value") is not None
    assert any("ADJUSTED_FCF" in w and "historical" in w for w in output.get("warnings", []))
