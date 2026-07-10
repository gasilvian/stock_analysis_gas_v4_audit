"""P2.3 tests: ECB/BNR FX loaders — official parses, precedence, provenance.

Pins: both official XML formats parse correctly (including BNR multipliers);
BNR is the RON-primary (direct exact/E0 beats ECB-derived cross); ECB cross
fallback is honestly approximation/E1; source divergence above tolerance is
warned, never averaged; unresolvable pairs stay MISSING; every generated row
enters operator_review_required.
"""
import json
import subprocess
import sys
from pathlib import Path

from sws_engine.rates.fx_loaders import (
    build_fx_curated_rows,
    parse_bnr_nbrfxrates_xml,
    parse_ecb_eurofxref_xml,
    write_fx_curated_csv,
)

ROOT = Path(__file__).resolve().parents[2]
ECB_XML = (ROOT / "tests/fixtures/rates/ecb_eurofxref_daily_sample.xml").read_text(encoding="utf-8")
BNR_XML = (ROOT / "tests/fixtures/rates/bnr_nbrfxrates_sample.xml").read_text(encoding="utf-8")


def test_parse_ecb_official_format():
    parsed = parse_ecb_eurofxref_xml(ECB_XML)
    assert parsed["date"] == "2026-07-09"
    assert parsed["base"] == "EUR"
    assert parsed["rates"]["USD"] == 1.1456
    assert parsed["rates"]["RON"] == 5.2388


def test_parse_bnr_official_format_with_multiplier():
    parsed = parse_bnr_nbrfxrates_xml(BNR_XML)
    assert parsed["date"] == "2026-07-09"
    assert parsed["base"] == "RON"
    assert parsed["rates"]["USD"] == 4.5744
    assert parsed["rates"]["HUF"] == 1.3110 / 100  # multiplier normalized


def test_bnr_direct_beats_ecb_cross_for_ron_pairs():
    ecb = parse_ecb_eurofxref_xml(ECB_XML)
    bnr = parse_bnr_nbrfxrates_xml(BNR_XML)
    result = build_fx_curated_rows(ecb=ecb, bnr=bnr, fetched_as_of="2026-07-10")
    by_pair = {r["pair"]: r for r in result["rows"]}
    assert by_pair["USDRON"]["source"] == "BNR_reference_rate"
    assert by_pair["USDRON"]["source_quality"] == "exact"
    assert by_pair["USDRON"]["source_class"] == "E0"
    assert by_pair["EURRON"]["source"] == "BNR_reference_rate"
    assert by_pair["EURUSD"]["source"] == "ECB_reference_rate"
    assert all(r["review_status"] == "operator_review_required" for r in result["rows"])
    # ECB-derived cross (5.2388/1.1456=4.5730) vs BNR 4.5744 -> 0.03% < 0.5%
    assert not any(w.startswith("FX_SOURCE_DIVERGENCE") for w in result["warnings"])


def test_ecb_cross_fallback_is_approximation_e1_when_no_bnr():
    ecb = parse_ecb_eurofxref_xml(ECB_XML)
    result = build_fx_curated_rows(ecb=ecb, bnr=None, pairs=["USDRON"], fetched_as_of="2026-07-10")
    row = result["rows"][0]
    assert row["source"] == "ECB_cross_derived"
    assert row["source_quality"] == "approximation"
    assert row["source_class"] == "E1"
    assert abs(float(row["rate"]) - 5.2388 / 1.1456) < 1e-6
    assert "not a directly published pair" in row["note"]


def test_source_divergence_is_warned_never_averaged():
    ecb = parse_ecb_eurofxref_xml(ECB_XML)
    bnr = parse_bnr_nbrfxrates_xml(BNR_XML)
    bnr["rates"]["USD"] = 4.70  # ~2.7% away from the ECB-derived 4.5730
    result = build_fx_curated_rows(ecb=ecb, bnr=bnr, pairs=["USDRON"], fetched_as_of="2026-07-10")
    row = result["rows"][0]
    assert float(row["rate"]) == 4.70  # BNR direct kept per RON-primary rule
    assert any(w.startswith("FX_SOURCE_DIVERGENCE") for w in result["warnings"])


def test_unresolvable_pair_stays_missing():
    ecb = parse_ecb_eurofxref_xml(ECB_XML)
    result = build_fx_curated_rows(ecb=ecb, bnr=None, pairs=["USDCHF"], fetched_as_of="2026-07-10")
    assert result["rows"] == []
    assert result["skipped"] == ["USDCHF"]
    assert any(w.startswith("FX_PAIR_UNRESOLVABLE") for w in result["warnings"])


def test_written_csv_is_readable_by_the_engine_fx_reader(tmp_path):
    from sws_engine.rates.rates import fx_rate
    ecb = parse_ecb_eurofxref_xml(ECB_XML)
    bnr = parse_bnr_nbrfxrates_xml(BNR_XML)
    result = build_fx_curated_rows(ecb=ecb, bnr=bnr, fetched_as_of="2026-07-10")
    path = write_fx_curated_csv(result["rows"], tmp_path / "fx.csv")
    assert fx_rate(path, "USDRON", "2026-07-10") == {"rate": 4.5744, "as_of": "2026-07-09", "pair": "USDRON"}


def test_cli_refresh_fx_smoke(tmp_path):
    out = tmp_path / "fx_eod_curated.csv"
    proc = subprocess.run(
        ["env", "PYTHONPATH=src", sys.executable, "-m", "sws_engine.cli", "refresh-fx",
         "--ecb-xml", str(ROOT / "tests/fixtures/rates/ecb_eurofxref_daily_sample.xml"),
         "--bnr-xml", str(ROOT / "tests/fixtures/rates/bnr_nbrfxrates_sample.xml"),
         "--output", str(out)],
        cwd=str(ROOT), text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    body = json.loads(proc.stdout)
    assert body["reason_code"] == "FX_CURATED_WRITTEN_REVIEW_REQUIRED"
    assert body["rows_written"] == 3
    assert out.exists()
