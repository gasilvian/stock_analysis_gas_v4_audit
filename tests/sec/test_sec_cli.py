import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def D(*p):
    return os.path.join(ROOT, *p)


def test_refresh_sec_financials_cli_command(tmp_path):
    from sws_engine.cli import main

    code = main([
        "refresh-sec-financials",
        "--tickers", "AAPL",
        "--output", str(tmp_path / "sec"),
        "--cik-map", D("tests", "fixtures", "sec", "company_tickers.json"),
        "--companyfacts-dir", D("tests", "fixtures", "sec", "companyfacts"),
        "--valuation-date", "2026-07-09",
    ])
    assert code == 0
    rep = json.loads((tmp_path / "sec" / "sec_refresh_report.json").read_text())
    assert rep["tickers_succeeded"][0]["ticker"] == "AAPL"
