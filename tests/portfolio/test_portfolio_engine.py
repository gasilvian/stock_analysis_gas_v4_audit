"""Portfolio engine tests (SPEC section 8)."""
import yaml

from sws_engine.portfolio.aggregation import aggregate_snowflake
from sws_engine.portfolio.corporate_actions import apply_split, reinvest_dividend
from sws_engine.portfolio.portfolio_run import run_portfolio_analysis
from sws_engine.portfolio.returns import portfolio_returns


def _scores(v, f, p, h, d):
    return {a: {"score_raw": s} for a, s in
            zip(("value", "future", "past", "health", "dividend"),
                (v, f, p, h, d))}


def test_snowflake_aggregation_contributor_invariant():
    positions = [
        {"ticker": "AAA", "weight": 0.5, "scores": _scores(5, 4, 6, 3, 2),
         "metrics": {"pe": 15, "pb": 3, "peg": 0.8}},
        {"ticker": "BBB", "weight": 0.3, "scores": _scores(2, 5, 3, 6, 4),
         "metrics": {"pe": 500, "pb": 2, "peg": 1.5}},  # PE above cap 200
        {"ticker": "ETF1", "weight": 0.2, "is_etf": True,
         "scores": _scores(6, 6, 6, 6, 6)},
    ]
    assumptions = {"outlier_caps": {"pe_max": 200, "pb_max": 50, "peg_max": 20}}
    agg = aggregate_snowflake(positions, assumptions)
    # ETF excluded from Snowflake
    assert agg["excluded_etf"] == ["ETF1"]
    # SPEC 8.2 invariant: contributors sum to portfolio axis score
    for axis, score in agg["axes"].items():
        total = sum(c["contributor_value"] for c in agg["contributors"][axis])
        assert abs(total - score) < 1e-9
    # weights renormalized over eligible positions: value = 5*0.625 + 2*0.375
    assert abs(agg["axes"]["value"] - (5 * 0.625 + 2 * 0.375)) < 1e-6
    # outlier cap applied: weighted PE uses 200, not 500
    assert abs(agg["weighted_metrics"]["pe"] - (0.625 * 15 + 0.375 * 200)) < 1e-6


def test_watchlist_and_holdings_synthetic_buys():
    payload = {
        "portfolio_type": "holdings", "valuation_date": "2026-07-06",
        "positions": [
            {"ticker": "AAA", "current_price": 10.0, "quantity": 100},
            {"ticker": "BBB", "current_price": 50.0, "quantity": 10},
        ],
    }
    out = run_portfolio_analysis(payload, {})
    r = out["returns_per_position"]
    # synthetic buys at valuation date: zero gain, AYI 0 -> CAGR suppressed
    assert abs(r["AAA"]["gain"]) < 1e-9
    assert r["AAA"]["cagr"] is None and r["AAA"]["cagr_suppressed_ayi_lt_1"]


def test_ayi_below_1_suppresses_cagr():
    r = portfolio_returns(
        [{"type": "buy", "date": "2026-05-01", "price": 10, "shares": 100}],
        current_price=12.0, valuation_date="2026-07-06")
    assert r["total_return"] > 0
    assert r["avg_years_invested"] < 1 and r["cagr"] is None


def test_dividends_not_reinvested_included_in_gain():
    r = portfolio_returns(
        [{"type": "buy", "date": "2024-07-06", "price": 10, "shares": 100}],
        current_price=10.0, valuation_date="2026-07-06",
        dividends_not_reinvested=50.0)
    assert abs(r["gain"] - 50.0) < 1e-9
    assert abs(r["total_return"] - 0.05) < 1e-9


def test_corporate_actions_split_rounds_up_and_reinvestment():
    assert apply_split(7, 3, 2) == 11          # 10.5 -> round UP
    assert apply_split(10, 2, 1) == 20         # exact stays exact
    assert abs(reinvest_dividend(33.0, 11.0) - 3.0) < 1e-9  # fractional @ 0 cost


def test_assumptions_yaml_registers_portfolio_policies(assumptions_path):
    with open(assumptions_path) as fh:
        a = yaml.safe_load(fh)
    assert a["portfolio_buy_duration_policy"]["source_class"] == "E1"
    assert a["portfolio_day_count"]["convention"] == "ACT/365.25"
    assert a["dcf_extrapolation_seed_policy"]["source_class"] == "E1"
