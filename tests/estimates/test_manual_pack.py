"""B4 tests: manual analyst-estimates pack — governance and injection.

The analyst-estimates family is the last honest-free-source gap (no free API
provides the SWS weighted format). These tests pin the operator workflow:
reviewed + unexpired packs inject with assumption/E3 lineage and enable the
SWS-faithful analyst-FCF valuation route; everything else is refused with an
explicit reason code and the payload stays untouched.
"""
import json
from pathlib import Path

from sws_engine.estimates.manual_pack import (
    apply_estimates_from_dir,
    apply_estimates_pack,
)

ROOT = Path(__file__).resolve().parents[2]


def _pack(**over):
    pack = {
        "ticker": "AAPL", "source": "manual_transcription",
        "source_detail": "test-pack", "source_as_of": "2026-07-01",
        "review_status": "reviewed", "expires_at": "2026-10-01",
        "currency": "USD",
        "earnings_estimates": [
            {"fiscal_year": 2026, "value": 112e9, "analysts": 30},
            {"fiscal_year": 2027, "value": 121e9, "analysts": 28},
            {"fiscal_year": 2028, "value": 130e9, "analysts": 18},
        ],
        "fcf_estimates": [
            {"fiscal_year": 2026, "value": 108e9},
            {"fiscal_year": 2027, "value": 116e9},
            {"fiscal_year": 2028, "value": 124e9},
        ],
    }
    pack.update(over)
    return pack


def test_reviewed_unexpired_pack_injects_with_e3_assumption_lineage():
    payload = {"ticker": "AAPL"}
    report = apply_estimates_pack(payload, _pack(), valuation_date="2026-07-10")
    assert report["reason_code"] == "ESTIMATES_INJECTED"
    assert set(report["applied_fields"]) == {"earnings_estimates", "fcf_estimates"}
    assert payload["earnings_estimates"][0] == {"value": 112e9, "analysts": 30}
    assert payload["fcf_estimates"][2] == {"value": 124e9}
    lin = payload["lineage"]["field_lineage"]["earnings_estimates"]
    assert lin["provider"] == "manual_estimates_pack"
    assert lin["source_quality"] == "assumption"
    assert lin["source_class"] == "E3"
    assert payload["analyst_estimates_as_of"] == "2026-07-01"
    assert any(w.startswith("MANUAL_ESTIMATES_INJECTED") for w in payload["builder_warnings"])


def test_unreviewed_expired_template_and_mismatch_are_refused_untouched():
    for over, reason in [
        (dict(review_status="operator_review_required"), "ESTIMATES_NOT_REVIEWED"),
        (dict(expires_at="2026-01-01"), "ESTIMATES_EXPIRED"),
        (dict(source="template_do_not_use"), "ESTIMATES_TEMPLATE_REFUSED"),
        (dict(ticker="MSFT"), "ESTIMATES_TICKER_MISMATCH"),
    ]:
        payload = {"ticker": "AAPL"}
        report = apply_estimates_pack(payload, _pack(**over), valuation_date="2026-07-10")
        assert report["status"] == "FAIL"
        assert report["reason_code"] == reason
        assert "earnings_estimates" not in payload


def test_weighted_format_is_validated():
    payload = {"ticker": "AAPL"}
    bad = _pack()
    bad["earnings_estimates"][1] = {"fiscal_year": 2027, "value": 121e9}  # no analysts
    report = apply_estimates_pack(payload, bad, valuation_date="2026-07-10")
    assert report["reason_code"] == "ESTIMATES_PACK_INVALID"
    assert "analysts" in report["warnings"][0]
    assert "earnings_estimates" not in payload


def test_existing_payload_values_are_preserved():
    payload = {"ticker": "AAPL", "fcf_estimates": [{"value": 1.0}]}
    report = apply_estimates_pack(payload, _pack(), valuation_date="2026-07-10")
    assert "fcf_estimates" in report["skipped_existing"]
    assert payload["fcf_estimates"] == [{"value": 1.0}]
    assert "earnings_estimates" in report["applied_fields"]


def test_stale_unavailability_warnings_are_cleaned_for_injected_fields():
    payload = {"ticker": "AAPL", "builder_warnings": [
        "PROVIDER_LIMITATION: fcf_estimates not available via yfinance; using adjusted FCF fallback if OCF/capex are available",
        "PROVIDER_LIMITATION: something else entirely",
    ]}
    apply_estimates_pack(payload, _pack(), valuation_date="2026-07-10")
    assert not any("fcf_estimates not available" in w for w in payload["builder_warnings"])
    assert any("something else entirely" in w for w in payload["builder_warnings"])


def test_directory_lookup_is_honest_when_absent(tmp_path):
    payload = {"ticker": "AAPL"}
    report = apply_estimates_from_dir(payload, tmp_path, valuation_date="2026-07-10")
    assert report["reason_code"] == "ESTIMATES_PACK_NOT_FOUND"
    assert "earnings_estimates" not in payload


def test_directory_lookup_injects_when_present(tmp_path):
    (tmp_path / "AAPL_analyst_estimates.json").write_text(json.dumps(_pack()), encoding="utf-8")
    payload = {"ticker": "AAPL"}
    report = apply_estimates_from_dir(payload, tmp_path, valuation_date="2026-07-10")
    assert report["reason_code"] == "ESTIMATES_INJECTED"
    assert payload["earnings_estimates"]


def test_repo_template_file_is_refused():
    template_path = ROOT / "data/real_sources/estimates/_TEMPLATE_analyst_estimates.json"
    pack = json.loads(template_path.read_text(encoding="utf-8"))
    payload = {"ticker": "TICKER"}
    report = apply_estimates_pack(payload, pack, valuation_date="2026-07-10", pack_path=template_path)
    assert report["reason_code"] == "ESTIMATES_TEMPLATE_REFUSED"


def test_analyst_fcf_route_changes_fair_value_vs_fallback():
    """SWS-faithful path: with fcf_estimates present, the two-stage DCF uses
    the analyst series instead of the ADJUSTED_FCF fallback and fair value
    changes accordingly on the enriched recorded AAPL payload."""
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

    def build():
        payload = map_yfinance_snapshot_to_input_payload(
            raw, valuation_date="2026-07-10", market="US", overrides=inj["overrides"])
        rec = resolve_cik("AAPL", ROOT / "tests/fixtures/sec/company_tickers.json")
        facts, src = get_companyfacts(rec.cik10, fixture_dir=ROOT / "tests/fixtures/sec/companyfacts", live=False)
        snap = build_statement_snapshot(facts, cik_record=rec, source_path=src, valuation_date="2026-07-10")
        apply_sec_payload_updates(payload, snap["payload_updates"])
        return payload

    base = build()
    fv_fallback = run_company_analysis(base, str(ROOT / "config/assumptions.yaml"), str(ROOT / "schemas/output_schema.json"))["fair_value"]

    enriched = build()
    apply_estimates_pack(enriched, _pack(), valuation_date="2026-07-10")
    out = run_company_analysis(enriched, str(ROOT / "config/assumptions.yaml"), str(ROOT / "schemas/output_schema.json"))
    assert out["fair_value"] is not None
    assert abs(out["fair_value"] - fv_fallback) > 1.0
    assert not any("ADJUSTED_FCF" in w for w in out.get("warnings", []))
