import csv
import json

from sws_engine.averages.builder import build_averages, load_universe, save_universe_coverage


def test_averages_country_region_global_fallback(tmp_path):
    path = tmp_path / "universe.csv"
    rows = [
        {"ticker":"A","kind":"stock","market":"US","country":"US","region":"NA","industry":"Tech","price":"100","eps":"5","shares_outstanding":"10","total_assets":"1000","intangible_assets":"100","total_liabilities":"400","market_cap":"1000","net_income_growth":"0.1","revenue_growth":"0.1","eps_growth":"0.1","roa":"0.08","dividend_yield":"0.01"},
        {"ticker":"B","kind":"stock","market":"US","country":"CA","region":"NA","industry":"Tech","price":"80","eps":"4","shares_outstanding":"10","total_assets":"900","intangible_assets":"90","total_liabilities":"300","market_cap":"800","net_income_growth":"0.1","revenue_growth":"0.1","eps_growth":"0.1","roa":"0.08","dividend_yield":"0.02"},
        {"ticker":"C","kind":"stock","market":"US","country":"CA","region":"NA","industry":"Tech","price":"60","eps":"3","shares_outstanding":"10","total_assets":"700","intangible_assets":"70","total_liabilities":"250","market_cap":"600","net_income_growth":"0.1","revenue_growth":"0.1","eps_growth":"0.1","roa":"0.08","dividend_yield":"0.03"},
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    snap = build_averages(load_universe(str(path)), as_of="2026-07-08", min_universe_count=2, source="real_curated_test", market_name="US")
    assert snap["meta"]["fallback_hierarchy"] == ["industry_country", "industry_region", "industry_global", "market"]
    assert snap["levels"]["industry_country"]["US|Tech"]["fallback_level"] in {"industry_region", "industry_global"}
    assert snap["market"]["pb_average"] is not None


def test_universe_coverage_report(tmp_path):
    src = "data/universe/universe_US_template.csv"
    out = tmp_path / "coverage.json"
    rows = load_universe(src)
    save_universe_coverage(rows, str(out))
    data = json.loads(out.read_text())
    assert data["rows"]
    assert "missing_required_fields" in data["rows"][0]
