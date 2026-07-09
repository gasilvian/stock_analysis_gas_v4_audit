def test_yfinance_degraded_has_warnings(run, demo_copy):
    p = demo_copy()
    p["provider_profile"] = "yfinance_pragmatic"
    # simulate fields yfinance cannot supply
    for f in ("roe_3y_estimate", "estimated_payout_3y", "intangible_assets",
              "market_averages", "industry_averages"):
        p.pop(f, None)
    out = run(p)
    assert out["provider_profile"] == "yfinance_pragmatic"
    assert any("PROVIDER_LIMITATION" in w for w in out["warnings"])
    assert any("not a faithful replication" in w for w in out["warnings"])

    def check(axis, cid):
        return next(c for c in out["checks"]
                    if c["axis"] == axis and c["id"] == cid)

    for axis, cid in (("future", 6), ("dividend", 6), ("value", 6)):
        c = check(axis, cid)
        assert c["result"] == "UNKNOWN", (axis, cid)
        assert c["reason_code"] == "PROVIDER_LIMITATION", (axis, cid)
    assert any("checks UNKNOWN due to provider limitations" in w
               for w in out["warnings"])
