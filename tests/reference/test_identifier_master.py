from sws_engine.reference.identifier_master import build_identifier_master, validate_identifier_master


def test_build_identifier_master_from_universe_and_cik_map(tmp_path):
    out = tmp_path / "identifier_master.csv"
    rep = build_identifier_master(
        universe_csv="tests/fixtures/reference/universe_us_minimal.csv",
        cik_map="tests/fixtures/reference/sec_company_tickers.json",
        output_csv=out,
        as_of="2026-07-09",
    )
    assert rep["status"] == "PASS_WITH_LIMITATIONS"
    assert rep["rows_written"] == 4
    text = out.read_text(encoding="utf-8")
    assert "AAPL" in text
    assert "0000320193" in text
    assert "fund_etf_excluded" in text
    val = validate_identifier_master(out)
    assert val["status"] == "PASS"
    assert val["rows_with_cik"] == 3


def test_identifier_master_require_reviewed_blocks_operator_review_required(tmp_path):
    out = tmp_path / "identifier_master.csv"
    build_identifier_master(
        universe_csv="tests/fixtures/reference/universe_us_minimal.csv",
        cik_map="tests/fixtures/reference/sec_company_tickers.json",
        output_csv=out,
        review_status="operator_review_required",
    )
    val = validate_identifier_master(out, require_reviewed=True)
    assert val["status"] == "NOT_READY"
    assert any(i["code"] == "IDENTIFIER_MASTER_REVIEW_REQUIRED" for i in val["issues"])
