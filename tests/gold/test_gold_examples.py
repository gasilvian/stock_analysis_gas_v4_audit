"""Gold tests from public SWS examples (test_suite.md tolerances)."""
import json
import os

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _load(name):
    with open(os.path.join(FIX, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_gold_amzn_dcf_2019_fair_value_and_decay():
    from sws_engine.valuation.two_stage_fcf import project_fcf, two_stage_fcf_value
    fx = _load("gold_amzn_dcf_2019.json")
    i, e = fx["input_snapshot"], fx["expected_output"]
    fv, det = two_stage_fcf_value(
        analyst_fcf=i["analyst_fcf_musd"], discount_rate=i["discount_rate"],
        long_run_growth=i["long_run_growth"], decay=0.7,
        shares_outstanding=i["shares_outstanding_m"])
    # spec-mandated tolerance: +/-0.1% on fair value (test_suite.md)
    assert abs(fv - e["fair_value_per_share"]) / e["fair_value_per_share"] < 0.001
    # intermediate components: +/-0.3% (public example rounds FCFs to USD
    # millions and rates to 2dp, which propagates into TV)
    assert abs(det["pv_stage1"] - e["pv_stage1_musd"]) / e["pv_stage1_musd"] < 0.003
    assert abs(det["terminal_value"] - e["terminal_value_musd"]) / e["terminal_value_musd"] < 0.003
    # full projection reproduces documented FCF path within rounding
    path = project_fcf(i["analyst_fcf_musd"], i["long_run_growth"], 0.7)
    for got, exp in zip(path, i["documented_full_path_musd"]):
        assert abs(got - exp) / exp < 0.002
    # decay recurrence r_t - g = 0.7 * (r_(t-1) - g) holds on documented path
    doc = i["documented_full_path_musd"]
    g = i["long_run_growth"]
    rates = [doc[t] / doc[t - 1] - 1 for t in range(6, 10)]
    for t in range(1, len(rates)):
        assert abs((rates[t] - g) / (rates[t - 1] - g) - 0.7) < 0.01


def test_gold_fb_growth_weighted_regression():
    from sws_engine.growth.analyst_regression import analyst_growth
    fx = _load("gold_fb_growth.json")
    g = analyst_growth(fx["input_snapshot"]["actual_earnings_busd"],
                       fx["input_snapshot"]["estimates"])
    assert abs(g - fx["expected_output"]["growth"]) < 0.005  # +/-0.5pp


def test_gold_hemacare_growth_method_c():
    from sws_engine.growth.fundamentals import fundamentals_growth
    fx = _load("gold_hemacare_growth.json")
    i = fx["input_snapshot"]
    g = fundamentals_growth(i["current_earnings_musd"], i["current_equity_musd"],
                            i["stable_roe"], i["industry_median_roe"],
                            i["stable_payout_ratio"])
    assert abs(g - fx["expected_output"]["growth"]) < 0.001  # +/-0.1pp


def test_gold_portfolio_amzn_returns():
    from sws_engine.portfolio.returns import portfolio_returns
    fx = _load("gold_portfolio_amzn.json")
    i, e = fx["input_snapshot"], fx["expected_output"]
    r = portfolio_returns(i["transactions"], current_price=i["current_price"],
                          valuation_date=i["valuation_date"])
    assert abs(r["gain"] - e["gain"]) < 0.01
    assert abs(r["total_return"] - e["total_return"]) < 0.001  # +/-0.1pp
    assert abs(r["avg_years_invested"] - e["avg_years_invested"]) < 0.01
    assert abs(r["cagr"] - e["cagr"]) < 0.005  # public example rounds AYI


def test_gold_fx_price_vs_currency_gain_split():
    from sws_engine.portfolio.fx import gain_split
    fx = _load("gold_fx_example.json")
    i, e = fx["input_snapshot"], fx["expected_output"]
    s = gain_split(i["cost_usd"], i["value_usd"],
                   i["fx_at_buy_eur_per_usd"], i["fx_current_eur_per_usd"])
    assert abs(s["combined_gain"] - e["combined_gain_eur"]) < 0.01
    assert abs(s["price_gain_portfolio_ccy"] - e["price_gain_eur"]) < 0.01
    assert abs(s["currency_gain"] - e["currency_gain_eur"]) < 0.01
