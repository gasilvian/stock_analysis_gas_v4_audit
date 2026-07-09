"""P1.3b tests: SEC payload merge with sec_precedence and conflict visibility.

Closes the 'SEC silo' gap (Post-P0.14 audit; calibration backlog B4/B8): the
refresh-sec-financials artifacts are now consumable by payload builders. The
tests pin the precedence doctrine, the never-degrade rule, conflict
visibility, profile preservation, and the end-to-end confidence effect on the
recorded AAPL snapshot.
"""
import json
from pathlib import Path

from sws_engine.providers.yfinance_mapper import map_yfinance_snapshot_to_input_payload
from sws_engine.sec.cik_resolver import resolve_cik
from sws_engine.sec.companyfacts_adapter import get_companyfacts
from sws_engine.sec.payload_merge import (
    apply_sec_payload_updates,
    merge_sec_updates_from_dir,
)
from sws_engine.sec.statement_snapshot import build_statement_snapshot

ROOT = Path(__file__).resolve().parents[2]


def _aapl_sec_updates(valuation_date="2026-07-10"):
    rec = resolve_cik("AAPL", ROOT / "tests/fixtures/sec/company_tickers.json")
    facts, src = get_companyfacts(rec.cik10, fixture_dir=ROOT / "tests/fixtures/sec/companyfacts", live=False)
    snap = build_statement_snapshot(facts, cik_record=rec, source_path=src, valuation_date=valuation_date)
    return snap["payload_updates"]


def _base_payload(**extra):
    payload = {
        "ticker": "AAPL",
        "provider_profile": "yfinance_pragmatic",
        "revenue": 410_000_000_000.0,
        "price": 210.0,
        "lineage": {"field_lineage": {
            "revenue": {"provider": "yfinance", "source_quality": "approximation", "source_class": "E3"},
            "price": {"provider": "yfinance", "source_quality": "approximation", "source_class": "E3"},
        }},
    }
    payload.update(extra)
    return payload


def test_merge_applies_values_with_verbatim_e0_lineage_and_preserves_profile():
    payload = _base_payload()
    report = apply_sec_payload_updates(payload, _aapl_sec_updates())
    assert report["status"] == "PASS"
    assert "revenue" in report["applied_fields"]
    assert payload["revenue"] == 391_035_000_000.0
    lin = payload["lineage"]["field_lineage"]["revenue"]
    assert lin["provider"] == "sec_companyfacts"
    assert lin["source_quality"] == "exact"
    assert lin["source_class"] == "E0"
    assert lin["tier"] == "official_filing"
    # profile is NOT flipped: per-field lineage carries the truth
    assert payload["provider_profile"] == "yfinance_pragmatic"
    # fields SEC does not cover are untouched
    assert payload["price"] == 210.0
    assert payload["lineage"]["field_lineage"]["price"]["provider"] == "yfinance"


def test_conflicts_are_visible_never_silent():
    payload = _base_payload()
    report = apply_sec_payload_updates(payload, _aapl_sec_updates())
    conflicts = {c["field"]: c for c in report["conflicts"]}
    assert "revenue" in conflicts
    rec = conflicts["revenue"]
    assert rec["base_value"] == 410_000_000_000.0
    assert rec["sec_value"] == 391_035_000_000.0
    assert rec["base_provider"] == "yfinance"
    assert rec["resolution"] == "sec_precedence"
    assert rec["relative_diff"] and rec["relative_diff"] > 0.005
    # mirrored into the payload for downstream audit visibility
    assert payload["source_conflicts"] == report["conflicts"]
    assert any(w.startswith("SOURCE_CONFLICT_DETECTED") for w in payload["builder_warnings"])
    assert any(w.startswith("SEC_ENRICHMENT_APPLIED") for w in payload["builder_warnings"])


def test_sec_missing_fields_never_blank_or_downgrade_base_values():
    payload = _base_payload(bank_deposits=123.0)
    payload["lineage"]["field_lineage"]["bank_deposits"] = {
        "provider": "manual_override", "source_quality": "exact", "source_class": "E3"}
    report = apply_sec_payload_updates(payload, _aapl_sec_updates())
    # AAPL SEC snapshot has bank_deposits as XBRL_TAG_MISSING -> must not touch
    assert payload["bank_deposits"] == 123.0
    assert payload["lineage"]["field_lineage"]["bank_deposits"]["provider"] == "manual_override"
    skipped = {s["field"] for s in report["skipped_missing"]}
    assert "bank_deposits" not in {f for f in report["applied_fields"]}
    # (the snapshot omits missing values from payload_updates entirely or
    # marks them missing; either way nothing was applied for the field)
    assert "bank_deposits" not in report["applied_fields"] or "bank_deposits" in skipped


def test_ticker_mismatch_aborts_without_mutation():
    payload = _base_payload(ticker="MSFT")
    before = json.dumps(payload, sort_keys=True)
    report = apply_sec_payload_updates(payload, _aapl_sec_updates())
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SEC_TICKER_MISMATCH"
    assert json.dumps(payload, sort_keys=True) == before


def test_close_values_within_tolerance_are_not_conflicts():
    updates = _aapl_sec_updates()
    payload = _base_payload(revenue=updates["revenue"] * 1.001)  # 0.1% apart
    report = apply_sec_payload_updates(payload, updates)
    assert "revenue" in report["applied_fields"]
    assert all(c["field"] != "revenue" for c in report["conflicts"])


def test_merge_from_dir_is_honest_when_artifact_absent(tmp_path):
    payload = _base_payload()
    before = json.dumps(payload, sort_keys=True)
    report = merge_sec_updates_from_dir(payload, tmp_path)
    assert report["reason_code"] == "SEC_UPDATES_NOT_FOUND"
    assert json.dumps(payload, sort_keys=True) == before


def test_merge_from_dir_finds_normalized_layout(tmp_path):
    updates = _aapl_sec_updates()
    norm = tmp_path / "normalized"
    norm.mkdir()
    (norm / "AAPL_sec_payload_updates.json").write_text(json.dumps(updates), encoding="utf-8")
    payload = _base_payload()
    report = merge_sec_updates_from_dir(payload, tmp_path)
    assert report["reason_code"] == "SEC_ENRICHMENT_APPLIED"
    assert payload["revenue"] == 391_035_000_000.0


def test_pragmatic_provider_honors_trusted_lineage_quality():
    """P1.3b: the yfinance_pragmatic profile no longer blanket-stamps
    SEC/curated/manual-enriched fields as approximation at check time;
    untraced fields keep the pragmatic approximation default."""
    from sws_engine.providers.yfinance_pragmatic import YFinancePragmaticProvider
    payload = _base_payload()
    apply_sec_payload_updates(payload, _aapl_sec_updates())
    pr = YFinancePragmaticProvider().prepare(payload)
    assert pr.field_quality["revenue"] == "exact"        # SEC-enriched
    assert pr.field_quality["price"] == "approximation"  # still yfinance


def test_end_to_end_confidence_effect_on_recorded_snapshot():
    """Recorded AAPL yfinance payload + SEC fixture: official_filing appears
    in the tier mix, at least one check reaches exact quality, and the
    confidence score does not decrease. Grade may legitimately stay low while
    analyst estimates / industry averages are missing — SEC cannot fix those."""
    from sws_engine.audit.audit_summary import build_audit_summary
    from sws_engine.orchestration.company_run import run_company_analysis

    raw = json.loads((ROOT / "data/recorded_yfinance/AAPL_snapshot.json").read_text(encoding="utf-8"))

    def run(with_sec):
        payload = map_yfinance_snapshot_to_input_payload(raw, valuation_date="2026-07-10", market="US")
        if with_sec:
            apply_sec_payload_updates(payload, _aapl_sec_updates())
        output = run_company_analysis(payload, str(ROOT / "config/assumptions.yaml"), str(ROOT / "schemas/output_schema.json"))
        summary = build_audit_summary(output, input_payload=payload)
        return summary["data_confidence"]

    base = run(False)
    enriched = run(True)
    assert enriched["source_tier_mix"].get("official_filing", 0) >= 15
    assert enriched["source_quality_mix"].get("exact", 0) >= 1
    assert enriched["confidence_score"] >= base["confidence_score"]
    # honesty: the still-missing curated inputs keep the UNKNOWN mass intact
    assert enriched["source_quality_mix"].get("missing", 0) == base["source_quality_mix"].get("missing", 0)
