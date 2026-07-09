def test_demo_complete_non_financial_runs_schema_valid(run, demo_payload):
    # run_company_analysis validates against output_schema.json internally;
    # reaching here without exception means the output is schema-valid.
    out = run(demo_payload)
    assert out["ticker"] == "DEMO"
    assert out["valuation_model"] == "two_stage_fcf"
    assert out["valuation_variant"] == "manual_input"
    assert out["fair_value"] == 120.0
    assert abs(out["discount_pct"] - (120.0 - 80.0) / 120.0) < 1e-9
    assert any("DEMO_FIXTURE_ONLY" in w for w in out["warnings"])
    assert any("NOT_INVESTMENT_ADVICE" in w for w in out["warnings"])
    assert out["lineage"]["price_as_of"] == "2026-07-03"


def test_unknown_scoring_no_normalization(run, demo_copy):
    p = demo_copy()
    # remove inputs so some value checks become UNKNOWN
    for f in ("intangible_assets", "roe_3y_estimate"):
        p.pop(f, None)
    out = run(p)
    for axis, s in out["scores"].items():
        assert set(s) == {"score_raw", "known_checks_count",
                          "unknown_checks_count", "coverage_pct"}
        assert "score_normalized" not in s
        assert s["known_checks_count"] + s["unknown_checks_count"] == 6
        assert abs(s["coverage_pct"] - s["known_checks_count"] / 6.0) < 1e-3
        # score_raw counts PASS out of a fixed denominator of 6
        assert 0 <= s["score_raw"] <= 6
    v = out["scores"]["value"]
    assert v["unknown_checks_count"] >= 1
