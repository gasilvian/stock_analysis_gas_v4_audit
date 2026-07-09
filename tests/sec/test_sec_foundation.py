import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def D(*p):
    return os.path.join(ROOT, *p)


def test_cik_resolver_sec_shape():
    from sws_engine.sec.cik_resolver import resolve_cik

    rec = resolve_cik("aapl", D("tests", "fixtures", "sec", "company_tickers.json"))
    assert rec is not None
    assert rec.cik10 == "0000320193"
    assert rec.exchange == "NasdaqGS"


def test_companyfacts_normalizes_declared_tags_only():
    from sws_engine.sec.cik_resolver import resolve_cik
    from sws_engine.sec.companyfacts_adapter import load_companyfacts_file
    from sws_engine.sec.statement_snapshot import build_statement_snapshot

    rec = resolve_cik("AAPL", D("tests", "fixtures", "sec", "company_tickers.json"))
    facts = load_companyfacts_file(D("tests", "fixtures", "sec", "companyfacts", "CIK0000320193.json"))
    snap = build_statement_snapshot(facts, cik_record=rec, source_path="fixture", valuation_date="2026-07-09")

    assert snap["status"] == "PASS_WITH_LIMITATIONS"
    assert snap["payload_updates"]["provider_profile"] == "sws_public_faithful_manual_inputs"
    assert snap["payload_updates"]["revenue"] == 391035000000
    assert snap["payload_updates"]["operating_cash_flow"] == 118254000000
    assert snap["payload_updates"]["capex_history_3y"] == [10708000000.0, 10959000000.0, 9447000000.0]
    assert snap["payload_updates"]["intangible_assets"] == 0.0
    lineage = snap["payload_updates"]["lineage"]["field_lineage"]
    assert lineage["revenue"]["source_id"] == "sec_companyfacts"
    assert lineage["revenue"]["tier"] == "official_filing"
    assert lineage["revenue"]["source_class"] == "E0"
    assert lineage["capex_history_3y"]["transform"] == "absolute_outflow_last_3y"


def test_missing_xbrl_tag_is_unknown_not_substituted():
    from sws_engine.sec.companyfacts_adapter import load_companyfacts_file
    from sws_engine.sec.xbrl_tag_resolver import latest_fact

    facts = load_companyfacts_file(D("tests", "fixtures", "sec", "companyfacts", "CIK0000019617.json"))
    fact = latest_fact(facts, "revenue")
    assert fact.value is None
    assert fact.reason_code == "XBRL_TAG_MISSING"


def test_bank_tag_partial_mapping():
    from sws_engine.sec.cik_resolver import resolve_cik
    from sws_engine.sec.companyfacts_adapter import load_companyfacts_file
    from sws_engine.sec.statement_snapshot import build_statement_snapshot

    rec = resolve_cik("JPM", D("tests", "fixtures", "sec", "company_tickers.json"))
    facts = load_companyfacts_file(D("tests", "fixtures", "sec", "companyfacts", "CIK0000019617.json"))
    snap = build_statement_snapshot(facts, cik_record=rec, source_path="fixture", valuation_date="2026-07-09")
    assert snap["payload_updates"]["bank_deposits"] == 2400000000000
    assert any(u["field"] == "revenue" and u["reason_code"] == "XBRL_TAG_MISSING" for u in snap["mapping_report"]["unmapped_fields"])


def test_refresh_sec_financials_cli_offline(tmp_path):
    from sws_engine.sec.workflow import refresh_sec_financials

    out = tmp_path / "sec"
    rep = refresh_sec_financials(
        tickers="AAPL,NOPE",
        output_dir=out,
        cik_map=D("tests", "fixtures", "sec", "company_tickers.json"),
        companyfacts_dir=D("tests", "fixtures", "sec", "companyfacts"),
        valuation_date="2026-07-09",
    )
    assert rep["status"] == "PASS_WITH_LIMITATIONS"
    assert len(rep["tickers_succeeded"]) == 1
    assert rep["tickers_skipped"][0]["reason_code"] == "CIK_NOT_FOUND"
    payload_path = out / "normalized" / "AAPL_sec_payload_updates.json"
    report_path = out / "mapping_reports" / "AAPL_sec_mapping_report.md"
    assert payload_path.exists()
    assert report_path.exists()
    payload = json.loads(payload_path.read_text())
    assert payload["lineage"]["sec_companyfacts_cik"] == "0000320193"
    assert "Not investment advice" in report_path.read_text()
