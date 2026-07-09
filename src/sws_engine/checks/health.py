"""HEALTH checks H1-H6 for non-financial companies (SPEC 5.4).

H6: E3 no-debt/no-interest policy (assumptions.yaml
health_no_interest_expense_policy) -> PASS with source_class=E3,
reason_code=ASSUMPTION_USED when active."""
from sws_engine.checks._helpers import CheckContext, binary_check
from sws_engine.core.enums import (
    Axis, CheckResultValue, ReasonCode, SourceClass, SourceQuality,
)
from sws_engine.core.result import CheckResult, unknown_check

FIN = ("financials_as_of",)


def run(ctx: CheckContext):
    checks = []
    st_a = ctx.num("st_assets")
    st_l = ctx.num("st_liabilities")
    lt_l = ctx.num("lt_liabilities")

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=1, name="st_assets_cover_st_liabilities",
        condition_inputs={"st_assets": st_a, "st_liabilities": st_l},
        lineage_fields=FIN, threshold="ST assets > ST liabilities",
        passes=st_a is not None and st_l is not None and st_a > st_l,
        quality_fields=("st_assets", "st_liabilities")))

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=2, name="st_assets_cover_lt_liabilities",
        condition_inputs={"st_assets": st_a, "lt_liabilities": lt_l},
        lineage_fields=FIN, threshold="ST assets > LT liabilities",
        passes=st_a is not None and lt_l is not None and st_a > lt_l,
        quality_fields=("st_assets", "lt_liabilities")))

    equity = ctx.num("equity")
    debt_c = ctx.num("debt_current")
    debt_5 = ctx.num("debt_5y_ago")
    equity_5 = ctx.num("equity_5y_ago")
    thr3 = "current D/E <= D/E 5 years ago"
    inputs3 = {"debt_current": debt_c, "equity": equity,
               "debt_5y_ago": debt_5, "equity_5y_ago": equity_5}
    if None in (debt_c, equity, debt_5, equity_5):
        checks.append(unknown_check(Axis.HEALTH, 3, "debt_to_equity_not_worse_5y",
                                    ReasonCode.MISSING_INPUT, inputs3, thr3,
                                    ctx.lineage(*FIN)))
    elif equity <= 0 or equity_5 <= 0:
        checks.append(unknown_check(Axis.HEALTH, 3, "debt_to_equity_not_worse_5y",
                                    ReasonCode.NEGATIVE_DENOMINATOR, inputs3, thr3,
                                    ctx.lineage(*FIN)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.HEALTH, id=3, name="debt_to_equity_not_worse_5y",
            condition_inputs=inputs3, lineage_fields=FIN, threshold=thr3,
            passes=(debt_c / equity) <= (debt_5 / equity_5),
            quality_fields=("debt_current", "equity", "debt_5y_ago", "equity_5y_ago")))

    thr4 = "D/E < 40%"
    inputs4 = {"debt_current": debt_c, "equity": equity}
    if debt_c is None or equity is None:
        checks.append(unknown_check(Axis.HEALTH, 4, "debt_to_equity_below_40pct",
                                    ReasonCode.MISSING_INPUT, inputs4, thr4,
                                    ctx.lineage(*FIN)))
    elif equity <= 0:
        checks.append(unknown_check(Axis.HEALTH, 4, "debt_to_equity_below_40pct",
                                    ReasonCode.NEGATIVE_DENOMINATOR, inputs4, thr4,
                                    ctx.lineage(*FIN)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.HEALTH, id=4, name="debt_to_equity_below_40pct",
            condition_inputs=inputs4, lineage_fields=FIN, threshold=thr4,
            passes=(debt_c / equity) < 0.40,
            quality_fields=("debt_current", "equity")))

    ocf = ctx.num("operating_cash_flow")
    tdebt = ctx.num("total_debt")
    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=5, name="ocf_covers_20pct_debt",
        condition_inputs={"operating_cash_flow": ocf, "total_debt": tdebt},
        lineage_fields=FIN, threshold="OCF > 20% * total debt",
        passes=ocf is not None and tdebt is not None and ocf > 0.20 * tdebt,
        quality_fields=("operating_cash_flow", "total_debt")))

    # H6 interest coverage with E3 no-debt policy
    ebit = ctx.num("ebit")
    nie = ctx.num("net_interest_expense")
    thr6 = "EBIT > 5 * net interest expense"
    inputs6 = {"ebit": ebit, "net_interest_expense": nie, "total_debt": tdebt}
    policy = (ctx.assumptions.get("health_no_interest_expense_policy") or {})
    policy_active = policy.get("default") == "PASS_if_no_debt_and_no_interest_expense"
    no_debt = tdebt is not None and tdebt == 0
    no_interest = nie is not None and nie <= 0
    if no_debt and no_interest:
        if policy_active:
            checks.append(CheckResult(
                axis=Axis.HEALTH, id=6, name="interest_coverage_above_5x",
                result=CheckResultValue.PASS,
                reason_code=ReasonCode.ASSUMPTION_USED,
                source_quality=SourceQuality.ASSUMPTION,
                source_class=SourceClass.E3,
                inputs=inputs6, threshold=thr6 + " (E3 no-debt policy)",
                input_lineage=ctx.lineage(*FIN)))
        else:
            checks.append(unknown_check(
                Axis.HEALTH, 6, "interest_coverage_above_5x",
                ReasonCode.NOT_APPLICABLE, inputs6, thr6,
                ctx.lineage(*FIN), source_class=SourceClass.E3))
    elif ebit is None or nie is None:
        checks.append(unknown_check(Axis.HEALTH, 6, "interest_coverage_above_5x",
                                    ReasonCode.MISSING_INPUT, inputs6, thr6,
                                    ctx.lineage(*FIN)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.HEALTH, id=6, name="interest_coverage_above_5x",
            condition_inputs=inputs6, lineage_fields=FIN, threshold=thr6,
            passes=ebit > 5 * nie, quality_fields=("ebit", "net_interest_expense")))
    return checks
