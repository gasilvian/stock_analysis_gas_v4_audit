def _check(out, axis, id):
    return next(c for c in out["checks"] if c["axis"] == axis and c["id"] == id)


def test_dividend_history_lt_10y_fails_d3_d4(run, demo_copy):
    p = demo_copy()
    p["dps_history_10y"] = [1.0, 1.1, 1.2]  # only 3 years
    out = run(p)
    for cid in (3, 4):
        c = _check(out, "dividend", cid)
        assert c["result"] == "FAIL"
        assert c["reason_code"] == "FAIL_BY_DEFAULT"


def test_dividend_drop_gt_10pct_fails_d3(run, demo_copy):
    p = demo_copy()
    p["dps_history_10y"] = [1.0, 1.05, 1.1, 0.9, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25]
    out = run(p)
    c = _check(out, "dividend", 3)
    assert c["result"] == "FAIL"
    assert c["reason_code"] == "OK"


def test_missing_tangible_bv_v6_unknown(run, demo_copy):
    p = demo_copy()
    p.pop("intangible_assets", None)
    out = run(p)
    c = _check(out, "value", 6)
    assert c["result"] == "UNKNOWN"
    assert c["reason_code"] in ("MISSING_INPUT", "PROVIDER_LIMITATION")
    assert c["source_quality"] == "missing"


def test_negative_equity_related_checks_unknown(run, demo_copy):
    p = demo_copy()
    p["equity"] = -100.0
    p["equity_5y_ago"] = -50.0
    out = run(p)
    for axis, cid in (("past", 4), ("health", 3), ("health", 4)):
        c = _check(out, axis, cid)
        assert c["result"] == "UNKNOWN", (axis, cid)
        assert c["reason_code"] == "NEGATIVE_DENOMINATOR"


def test_negative_eps_pe_peg_unknown(run, demo_copy):
    p = demo_copy()
    p["eps"] = -1.5
    out = run(p)
    for cid in (3, 4, 5):
        c = _check(out, "value", cid)
        assert c["result"] == "UNKNOWN"
        assert c["reason_code"] == "NEGATIVE_DENOMINATOR"


def test_no_debt_no_interest_h6_passes_by_e3_policy(run, demo_copy):
    p = demo_copy()
    p["total_debt"] = 0
    p["net_interest_expense"] = 0
    out = run(p)
    c = _check(out, "health", 6)
    assert c["result"] == "PASS"
    assert c["reason_code"] == "ASSUMPTION_USED"
    assert c["source_class"] == "E3"


def test_strict_mode_does_not_autofill_missing_inputs(run, demo_copy):
    p = demo_copy()
    p.pop("fair_value", None)
    out = run(p)
    assert out["fair_value"] is None
    assert out["discount_pct"] is None
    assert out["valuation_variant"] == "unknown"
    for cid in (1, 2):
        c = _check(out, "value", cid)
        assert c["result"] == "UNKNOWN"
        assert c["reason_code"] == "MISSING_INPUT"
        assert c["inputs"]["fair_value"] is None
