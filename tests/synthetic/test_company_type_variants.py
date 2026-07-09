"""Synthetic tests for model selection, health variants and growth fallback
(test_suite.md: syn_reit_no_affo_ffo, syn_bank_missing_npl_deposits,
syn_missing_estimates, loss-making runway)."""


def _check(out, axis, id):
    return next(c for c in out["checks"] if c["axis"] == axis and c["id"] == id)


def test_reit_without_affo_ffo_nav_fallback_or_unknown(run, demo_copy):
    p = demo_copy()
    p["company_type"] = "reit"
    p.pop("fair_value", None)
    # NAV available -> nav_fallback
    p["affo_ffo_nav"] = {"nav_per_share": 95.0}
    out = run(p)
    assert out["valuation_model"] == "affo_dcf"
    assert out["valuation_variant"] == "nav_fallback"
    assert out["fair_value"] == 95.0
    assert out["valuation_model_source_class"] == "E3"
    # nothing available -> unknown, fair_value null
    p2 = demo_copy()
    p2["company_type"] = "reit"
    p2.pop("fair_value", None)
    p2["affo_ffo_nav"] = {}
    out2 = run(p2)
    assert out2["valuation_variant"] == "unknown"
    assert out2["fair_value"] is None


def test_reit_payout_threshold_100pct(run, demo_copy):
    p = demo_copy()
    p["company_type"] = "reit"
    p["affo_ffo_nav"] = {"nav_per_share": 95.0}
    p["payout_ratio"] = 0.95  # would FAIL for non-REIT (cap 90%)
    out = run(p)
    c = _check(out, "dividend", 5)
    assert c["result"] == "PASS"
    assert "100%" in c["threshold"]


def test_bank_missing_npl_deposits_hf_checks_unknown(run, demo_copy):
    p = demo_copy()
    p["company_type"] = "bank"
    p.pop("fair_value", None)
    p["bank_deposits_npl_chargeoffs"] = {}  # bank data unavailable
    out = run(p)
    # DDM branch (insufficient bank data), no expected_dps -> unknown variant
    assert out["valuation_model"] == "ddm"
    names = {c["id"]: c for c in out["checks"] if c["axis"] == "health"}
    for cid in (2, 3, 4, 5, 6):  # NPL/deposits/loans-dependent checks
        assert names[cid]["result"] == "UNKNOWN", cid
    # HF1 uses assets/equity which exist in fixture
    assert names[1]["result"] in ("PASS", "FAIL")
    assert names[1]["name"].startswith("hf_")


def test_bank_with_stable_roe_uses_excess_returns(run, demo_copy):
    p = demo_copy()
    p["company_type"] = "bank"
    p.pop("fair_value", None)
    p.update({"stable_future_roe": 0.14, "stable_future_bve": 3.0e9,
              "current_bve": 2.4e9, "discount_rate": 0.09,
              "excess_returns_expected_growth": 0.032})
    out = run(p)
    assert out["valuation_model"] == "excess_returns"
    assert out["valuation_variant"] == "base"
    # (0.14-0.09)*3e9/(0.09-0.032)=2.586e9; (2.4e9+2.586e9)/1e8 = 49.86
    assert abs(out["fair_value"] - 49.86) < 0.1


def test_loss_making_switches_to_cash_runway(run, demo_copy):
    p = demo_copy()
    p["current_eps"] = -1.2
    p["eps_history"] = [-0.5, -0.8, -1.2]
    p["cash_and_st_investments"] = 500.0
    p["annual_free_cash_burn"] = 300.0
    p["cash_burn_growth_3y"] = 1.0   # burn doubles: 600 > 500 cash
    out = run(p)
    h = {c["id"]: c for c in out["checks"] if c["axis"] == "health"}
    assert h[5]["name"] == "cash_covers_stable_burn_1y"
    assert h[5]["result"] == "PASS"   # 500 > 300 stable burn
    assert h[6]["name"] == "cash_covers_growing_burn_1y"
    assert h[6]["result"] == "FAIL"   # 500 < 300*(1+1.0)=600 grown burn


def test_growth_fallback_routes():
    from sws_engine.growth.fundamentals import resolve_growth
    # A: analyst
    g, route = resolve_growth({
        "current_earnings_abs": 10.0,
        "earnings_estimates": [{"value": 12, "analysts": 5},
                               {"value": 14, "analysts": 4},
                               {"value": 16, "analysts": 3}]})
    assert route == "analyst" and g > 0
    # B: historical (min 3 years)
    g, route = resolve_growth({"earnings_history": [8.0, 9.0, 10.0]})
    assert route == "historical" and abs(g - 1.0 / 9.0) < 0.02
    # C: fundamentals
    g, route = resolve_growth({
        "current_earnings_abs": 4.43, "equity": 10.27, "stable_roe": 0.302,
        "industry_median_roe": 0.138, "stable_payout_ratio": 0.0})
    assert route == "fundamentals" and abs(g - 0.0185) < 0.001
    # nothing -> None
    g, route = resolve_growth({})
    assert g is None and route is None


def test_two_stage_from_adjusted_fcf_no_estimates(run, demo_copy):
    p = demo_copy()
    p.pop("fair_value", None)
    p["capex_history_3y"] = [100e6, 140e6, 120e6]
    p["earnings_history"] = [300e6, 340e6, 380e6, 430e6, 480e6]
    p["levered_beta"] = 1.1  # cost of equity = 0.032 + 1.1*0.055 = 9.25%
    out = run(p)
    assert out["valuation_model"] == "two_stage_fcf"
    assert out["fair_value"] is not None and out["fair_value"] > 0
    assert any("ADJUSTED_FCF" in w for w in out["warnings"])


def test_management_flags_optional_and_excluded_from_scores(run, demo_copy):
    p = demo_copy()
    p["include_management"] = True
    p["management"] = {"ceo_total_compensation": 12e6,
                       "ceo_comp_cohort_median": 8e6,
                       "management_avg_tenure_years": 1.5,
                       "board_avg_tenure_years": 6.0,
                       "insider_shares_sold_12m": 100000,
                       "insider_shares_bought_12m": 20000,
                       "ceo_pay_rising": True, "eps_falling": False}
    out = run(p)
    mgmt = [c for c in out["checks"] if c["axis"] == "management"]
    snow = [c for c in out["checks"] if c["axis"] != "management"]
    assert len(mgmt) == 5 and len(snow) == 30
    # scores identical to run without management
    p2 = demo_copy()
    out2 = run(p2)
    assert out["scores"] == out2["scores"]
