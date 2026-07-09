"""PAST checks P1-P6 (SPEC 5.3)."""
from sws_engine.checks._helpers import CheckContext, binary_check
from sws_engine.core.enums import Axis, ReasonCode, SourceClass
from sws_engine.core.result import unknown_check

FIN = ("financials_as_of",)
FIN_IND = ("financials_as_of", "industry_averages_as_of")


def run(ctx: CheckContext):
    checks = []

    eps_g_1y = ctx.num("eps_growth_1y")
    ind_eps_g = ctx.nested_num("industry_averages", "eps_growth")
    checks.append(binary_check(
        ctx, axis=Axis.PAST, id=1, name="eps_growth_1y_above_industry",
        condition_inputs={"eps_growth_1y": eps_g_1y,
                          "industry_eps_growth": ind_eps_g},
        lineage_fields=FIN_IND,
        threshold="1y EPS growth > industry average EPS growth",
        passes=eps_g_1y is not None and ind_eps_g is not None and eps_g_1y > ind_eps_g,
        quality_fields=("eps_growth_1y", "industry_averages")))

    cur_eps = ctx.num("current_eps")
    eps5 = ctx.num("eps_5y_ago")
    checks.append(binary_check(
        ctx, axis=Axis.PAST, id=2, name="eps_above_5y_ago",
        condition_inputs={"current_eps": cur_eps, "eps_5y_ago": eps5},
        lineage_fields=FIN, threshold="current EPS > EPS 5 years ago",
        passes=cur_eps is not None and eps5 is not None and cur_eps > eps5,
        quality_fields=("current_eps", "eps_5y_ago")))

    g5avg = ctx.num("eps_growth_5y_avg")
    checks.append(binary_check(
        ctx, axis=Axis.PAST, id=3, name="current_eps_growth_above_5y_average",
        condition_inputs={"eps_growth_1y": eps_g_1y, "eps_growth_5y_avg": g5avg},
        lineage_fields=FIN,
        threshold="LTM YoY EPS growth > 5y avg annual EPS growth",
        passes=eps_g_1y is not None and g5avg is not None and eps_g_1y > g5avg,
        source_class=SourceClass.E0,
        quality_fields=("eps_growth_1y", "eps_growth_5y_avg")))

    # P4 ROE > 20%, UNKNOWN if equity <= 0 / missing
    roe = ctx.num("roe")
    equity = ctx.num("equity")
    thr = "ROE > 20%"
    inputs = {"roe": roe, "equity": equity}
    if equity is None or roe is None:
        checks.append(unknown_check(Axis.PAST, 4, "roe_above_20pct",
                                    ReasonCode.MISSING_INPUT, inputs, thr,
                                    ctx.lineage(*FIN)))
    elif equity <= 0:
        checks.append(unknown_check(Axis.PAST, 4, "roe_above_20pct",
                                    ReasonCode.NEGATIVE_DENOMINATOR, inputs, thr,
                                    ctx.lineage(*FIN)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.PAST, id=4, name="roe_above_20pct",
            condition_inputs=inputs, lineage_fields=FIN, threshold=thr,
            passes=roe > 0.20, quality_fields=("roe", "equity")))

    roce_c = ctx.num("roce_current")
    roce_3 = ctx.num("roce_3y_ago")
    checks.append(binary_check(
        ctx, axis=Axis.PAST, id=5, name="roce_improved_3y",
        condition_inputs={"roce_current": roce_c, "roce_3y_ago": roce_3},
        lineage_fields=FIN, threshold="current ROCE > ROCE 3 years ago",
        passes=roce_c is not None and roce_3 is not None and roce_c > roce_3,
        quality_fields=("roce_current", "roce_3y_ago")))

    roa = ctx.num("roa")
    ind_roa = ctx.nested_num("industry_averages", "roa")
    checks.append(binary_check(
        ctx, axis=Axis.PAST, id=6, name="roa_above_industry",
        condition_inputs={"roa": roa, "industry_roa": ind_roa},
        lineage_fields=FIN_IND, threshold="ROA > industry average ROA",
        passes=roa is not None and ind_roa is not None and roa > ind_roa,
        quality_fields=("roa", "industry_averages")))
    return checks
