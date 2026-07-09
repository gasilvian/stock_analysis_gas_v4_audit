"""Offline tests for create-curated-universe-from-yfinance."""
import csv

from sws_engine.ops import curated_universe as cu


def _mock_info(ticker, refresh=False):
    if ticker == "NOMETA":
        return {}
    if ticker == "JPM":
        return {"exchange": "NYQ", "country": "United States",
                "sector": "Financial Services", "industry": "Banks - Diversified",
                "currency": "USD"}
    return {"exchange": "NMS", "country": "United States",
            "sector": "Technology", "industry": "Consumer Electronics",
            "currency": "USD"}


def test_curated_universe_marks_source_and_unknowns(tmp_path, monkeypatch):
    monkeypatch.setattr(cu, "_fetch_info", _mock_info)
    out_csv = tmp_path / "universe_US_curated.csv"
    report = tmp_path / "universe_creation_report.md"
    summary = cu.create_curated_universe(
        tickers="AAPL,JPM,NOMETA", market="US",
        output_path=str(out_csv), report_path=str(report))
    assert summary["rows_written"] == 3
    with open(out_csv, newline="", encoding="utf-8") as fh:
        rows = {r["ticker"]: r for r in csv.DictReader(fh)}
    # source/notes tags are mandatory; no sample/template/synthetic wording
    for row in rows.values():
        assert row["source"] == "yfinance_live_pragmatic_curated"
        assert "operator-reviewed" in row["notes"]
        for banned in ("sample", "template", "synthetic"):
            assert banned not in row["source"].lower()
            assert banned not in row["notes"].lower()
    # missing metadata becomes UNKNOWN, never invented
    assert rows["NOMETA"]["sector"] == "UNKNOWN"
    assert rows["NOMETA"]["industry"] == "UNKNOWN"
    assert rows["NOMETA"]["company_type"] == "UNKNOWN"
    # financial sector requires operator review for company_type
    assert rows["JPM"]["company_type"] == "UNKNOWN"
    assert rows["AAPL"]["company_type"] == "non_financial"
    # warnings are reported, not silently absorbed
    assert any("NOMETA" in w for w in summary["warnings"])
    assert report.exists()


def test_curated_universe_isolates_fetch_failures(tmp_path, monkeypatch):
    def _boom(ticker, refresh=False):
        if ticker == "BOOM":
            raise RuntimeError("network down")
        return _mock_info(ticker)
    monkeypatch.setattr(cu, "_fetch_info", _boom)
    summary = cu.create_curated_universe(
        tickers="AAPL,BOOM", market="US",
        output_path=str(tmp_path / "u.csv"),
        report_path=str(tmp_path / "r.md"))
    assert summary["rows_written"] == 1
    assert summary["tickers_failed"][0]["ticker"] == "BOOM"
