"""FUTURE checks F1-F6 (SPEC 5.2)."""
from sws_engine.checks._helpers import CheckContext, binary_check
from sws_engine.core.enums import Axis, ReasonCode
from sws_engine.core.result import unknown_check

EST = ("analyst_estimates_as_of",)


def run(ctx: CheckContext):
    checks = []
    eg = ctx.num("earnings_growth")
    rg = ctx.num("revenue_growth")
    savings = ctx.nested_num("market_averages", "savings_rate")
    cpi = ctx.nested_num("market_averages", "cpi")
    becomes_profitable = ctx.payload.get("becomes_profitable_in_5y")

    # F1: earnings growth > savings + CPI OR becomes profitable in 5 years
    thr = "earnings_growth > savings_rate + CPI OR becomes profitable in 5y"
    inputs = {"earnings_growth": eg, "savings_rate": savings, "cpi": cpi,
              "becomes_profitable_in_5y": becomes_profitable}
    if becomes_profitable is True:
        checks.append(binary_check(
            ctx, axis=Axis.FUTURE, id=1, name="earnings_growth_above_savings_cpi",
            condition_inputs={"becomes_profitable_in_5y": True},
            lineage_fields=EST, threshold=thr, passes=True,
            quality_fields=("earnings_growth",)))
    elif eg is None or savings is None or cpi is None:
        checks.append(unknown_check(Axis.FUTURE, 1,
                                    "earnings_growth_above_savings_cpi",
                                    ReasonCode.MISSING_INPUT, inputs, thr,
                                    ctx.lineage(*EST)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.FUTURE, id=1, name="earnings_growth_above_savings_cpi",
            condition_inputs=inputs, lineage_fields=EST, threshold=thr,
            passes=eg > savings + cpi, quality_fields=("earnings_growth",)))

    mk_ni = ctx.nested_num("market_averages", "net_income_growth")
    checks.append(binary_check(
        ctx, axis=Axis.FUTURE, id=2, name="earnings_growth_above_market",
        condition_inputs={"earnings_growth": eg, "market_net_income_growth": mk_ni},
        lineage_fields=EST + ("industry_averages_as_of",),
        threshold="earnings_growth > market weighted net income growth",
        passes=(eg or 0) > (mk_ni or 0) if eg is not None and mk_ni is not None else False,
        quality_fields=("earnings_growth", "market_averages")))

    mk_rev = ctx.nested_num("market_averages", "revenue_growth")
    checks.append(binary_check(
        ctx, axis=Axis.FUTURE, id=3, name="revenue_growth_above_market",
        condition_inputs={"revenue_growth": rg, "market_revenue_growth": mk_rev},
        lineage_fields=EST + ("industry_averages_as_of",),
        threshold="revenue_growth > market weighted revenue growth",
        passes=(rg or 0) > (mk_rev or 0) if rg is not None and mk_rev is not None else False,
        quality_fields=("revenue_growth", "market_averages")))

    checks.append(binary_check(
        ctx, axis=Axis.FUTURE, id=4, name="earnings_growth_above_20pct",
        condition_inputs={"earnings_growth": eg}, lineage_fields=EST,
        threshold="earnings_growth > 20%",
        passes=eg is not None and eg > 0.20,
        quality_fields=("earnings_growth",)))

    checks.append(binary_check(
        ctx, axis=Axis.FUTURE, id=5, name="revenue_growth_above_20pct",
        condition_inputs={"revenue_growth": rg}, lineage_fields=EST,
        threshold="revenue_growth > 20%",
        passes=rg is not None and rg > 0.20,
        quality_fields=("revenue_growth",)))

    roe3 = ctx.num("roe_3y_estimate")
    checks.append(binary_check(
        ctx, axis=Axis.FUTURE, id=6, name="roe_3y_above_20pct",
        condition_inputs={"roe_3y_estimate": roe3}, lineage_fields=EST,
        threshold="estimated ROE in 3 years > 20%",
        passes=roe3 is not None and roe3 > 0.20,
        quality_fields=("roe_3y_estimate",)))
    return checks
