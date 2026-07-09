"""DIVIDEND checks D1-D6 (SPEC 5.7).

- D3/D4: direct DPS rules; history < 10 years => FAIL with
  reason_code=FAIL_BY_DEFAULT (documented rule). The 10y DPS regression is
  informative only and never drives D3/D4 (P0 fix in v3.1).
- Dividend gate (assumptions.yaml dividend_gate_policy, E0/E3): if yield is
  in the bottom 10th percentile of the market, D3-D6 return UNKNOWN with
  reason_code=DIVIDEND_GATE_LOW_YIELD.
"""
from sws_engine.checks._helpers import CheckContext, binary_check
from sws_engine.core.enums import (
    Axis, CheckResultValue, ReasonCode, SourceClass, SourceQuality,
)
from sws_engine.core.result import CheckResult, unknown_check

EST = ("analyst_estimates_as_of",)
FIN = ("financials_as_of",)
IND = ("industry_averages_as_of",)


def _gate_active(ctx):
    policy = (ctx.assumptions.get("dividend_gate_policy") or {})
    if "bottom_10pct" not in str(policy.get("default", "")):
        return False
    y = ctx.num("dividend_yield")
    p10 = ctx.nested_num("market_averages", "dividend_yield_p10")
    return y is not None and p10 is not None and y < p10


def _fail_by_default(ctx, id, name, inputs, threshold):
    return CheckResult(
        axis=Axis.DIVIDEND, id=id, name=name,
        result=CheckResultValue.FAIL,
        reason_code=ReasonCode.FAIL_BY_DEFAULT,
        source_quality=SourceQuality.EXACT,
        source_class=SourceClass.E0,
        inputs=inputs, threshold=threshold, input_lineage=ctx.lineage(*FIN))


def run(ctx: CheckContext):
    checks = []
    y = ctx.num("dividend_yield")
    p25 = ctx.nested_num("market_averages", "dividend_yield_p25")
    p75 = ctx.nested_num("market_averages", "dividend_yield_p75")

    checks.append(binary_check(
        ctx, axis=Axis.DIVIDEND, id=1, name="yield_above_market_p25",
        condition_inputs={"dividend_yield": y, "market_p25": p25},
        lineage_fields=IND, threshold="yield > market P25",
        passes=y is not None and p25 is not None and y > p25,
        quality_fields=("dividend_yield", "market_averages")))

    checks.append(binary_check(
        ctx, axis=Axis.DIVIDEND, id=2, name="yield_above_market_p75",
        condition_inputs={"dividend_yield": y, "market_p75": p75},
        lineage_fields=IND, threshold="yield > market P75",
        passes=y is not None and p75 is not None and y > p75,
        quality_fields=("dividend_yield", "market_averages")))

    gate = _gate_active(ctx)
    dps = ctx.payload.get("dps_history_10y")
    dps = [float(x) for x in dps] if isinstance(dps, (list, tuple)) else None

    # D3 stable dividend 10y
    thr3 = "no annual DPS decline > 10% over 10 years"
    inputs3 = {"dps_history_10y": dps, "history_years": len(dps) if dps else 0}
    if gate:
        checks.append(unknown_check(Axis.DIVIDEND, 3, "stable_dividend_10y",
                                    ReasonCode.DIVIDEND_GATE_LOW_YIELD,
                                    inputs3, thr3, ctx.lineage(*FIN),
                                    source_class=SourceClass.E3))
    elif dps is None or len(dps) < 10:
        checks.append(_fail_by_default(ctx, 3, "stable_dividend_10y", inputs3, thr3))
    else:
        declines = [
            (prev - cur) / prev
            for prev, cur in zip(dps[:-1], dps[1:]) if prev > 0
        ]
        max_decline = max(declines) if declines else 0.0
        inputs3["max_annual_decline"] = max_decline
        checks.append(binary_check(
            ctx, axis=Axis.DIVIDEND, id=3, name="stable_dividend_10y",
            condition_inputs=inputs3, lineage_fields=FIN, threshold=thr3,
            passes=max_decline <= 0.10, quality_fields=("dps_history_10y",)))

    # D4 dividend higher than 10y ago
    thr4 = "current annualized DPS > annualized DPS 10 years ago"
    inputs4 = {"dps_history_10y": dps, "history_years": len(dps) if dps else 0}
    if gate:
        checks.append(unknown_check(Axis.DIVIDEND, 4, "dividend_higher_than_10y_ago",
                                    ReasonCode.DIVIDEND_GATE_LOW_YIELD,
                                    inputs4, thr4, ctx.lineage(*FIN),
                                    source_class=SourceClass.E3))
    elif dps is None or len(dps) < 10:
        checks.append(_fail_by_default(ctx, 4, "dividend_higher_than_10y_ago",
                                       inputs4, thr4))
    else:
        inputs4.update({"dps_current": dps[-1], "dps_10y_ago": dps[0]})
        checks.append(binary_check(
            ctx, axis=Axis.DIVIDEND, id=4, name="dividend_higher_than_10y_ago",
            condition_inputs=inputs4, lineage_fields=FIN, threshold=thr4,
            passes=dps[-1] > dps[0], quality_fields=("dps_history_10y",)))

    is_reit = (ctx.payload.get("company_type") or "").lower() == "reit"
    cap = 1.00 if is_reit else 0.90

    # D5 current payout
    payout = ctx.num("payout_ratio")
    thr5 = f"0% < payout < {int(cap*100)}%"
    if gate:
        checks.append(unknown_check(Axis.DIVIDEND, 5, "current_payout_sustainable",
                                    ReasonCode.DIVIDEND_GATE_LOW_YIELD,
                                    {"payout_ratio": payout}, thr5,
                                    ctx.lineage(*FIN), source_class=SourceClass.E3))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.DIVIDEND, id=5, name="current_payout_sustainable",
            condition_inputs={"payout_ratio": payout}, lineage_fields=FIN,
            threshold=thr5,
            passes=payout is not None and 0 < payout < cap,
            quality_fields=("payout_ratio",)))

    # D6 estimated payout +3y
    payout3 = ctx.num("estimated_payout_3y")
    thr6 = f"0% < estimated payout +3y < {int(cap*100)}%"
    if gate:
        checks.append(unknown_check(Axis.DIVIDEND, 6, "future_payout_sustainable",
                                    ReasonCode.DIVIDEND_GATE_LOW_YIELD,
                                    {"estimated_payout_3y": payout3}, thr6,
                                    ctx.lineage(*EST), source_class=SourceClass.E3))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.DIVIDEND, id=6, name="future_payout_sustainable",
            condition_inputs={"estimated_payout_3y": payout3},
            lineage_fields=EST, threshold=thr6,
            passes=payout3 is not None and 0 < payout3 < cap,
            quality_fields=("estimated_payout_3y",)))
    return checks
