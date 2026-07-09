"""VALUE checks V1-V6 (SPEC 5.1 / check_engine_contract.md)."""
from sws_engine.checks._helpers import CheckContext, binary_check, quality_for
from sws_engine.core.enums import Axis, ReasonCode, SourceClass, SourceQuality
from sws_engine.core.result import CheckResult, unknown_check
from sws_engine.valuation.relative import compute_pb, compute_pe, compute_peg

FIN = ("financials_as_of",)
PRICE_FIN = ("price_as_of", "financials_as_of")
PRICE_IND = ("price_as_of", "industry_averages_as_of")


def _fv_check(ctx, id, name, factor, fair_value):
    price = ctx.num("price")
    inputs = {"price": price, "fair_value": fair_value, "factor": factor}
    threshold = f"Price <= Fair_Value * {factor}"
    if price is None or fair_value is None:
        return unknown_check(Axis.VALUE, id, name, ReasonCode.MISSING_INPUT,
                             inputs, threshold, ctx.lineage("price_as_of"))
    return binary_check(
        ctx, axis=Axis.VALUE, id=id, name=name,
        condition_inputs=inputs, lineage_fields=("price_as_of",),
        threshold=threshold, passes=price <= fair_value * factor,
        quality_fields=("price", "fair_value"),
    )


def _pe_vs_median(ctx, id, name, median, median_field, lineage_fields):
    pe, reason = compute_pe(ctx.payload)
    inputs = {"pe": pe, "benchmark": median}
    threshold = f"0 < PE < {median_field}"
    if pe is None:
        return unknown_check(Axis.VALUE, id, name, reason, inputs, threshold,
                             ctx.lineage(*lineage_fields))
    if median is None:
        return unknown_check(Axis.VALUE, id, name, ReasonCode.MISSING_INPUT,
                             inputs, threshold, ctx.lineage(*lineage_fields))
    return binary_check(
        ctx, axis=Axis.VALUE, id=id, name=name,
        condition_inputs=inputs, lineage_fields=lineage_fields,
        threshold=threshold, passes=0 < pe < median,
        quality_fields=("price", "eps"),
    )


def run(ctx: CheckContext, fair_value):
    checks = []
    checks.append(_fv_check(ctx, 1, "trading_below_fair_value_20pct", 0.80, fair_value))
    checks.append(_fv_check(ctx, 2, "trading_below_fair_value_40pct", 0.60, fair_value))

    checks.append(_pe_vs_median(
        ctx, 3, "pe_below_market",
        ctx.nested_num("market_averages", "pe_median_profitable"),
        "market_PE_median_profitable", ("price_as_of", "industry_averages_as_of")))
    checks.append(_pe_vs_median(
        ctx, 4, "pe_below_industry",
        ctx.nested_num("industry_averages", "pe_median_profitable"),
        "industry_PE_median_profitable", ("price_as_of", "industry_averages_as_of")))

    # V5 PEG
    peg, reason = compute_peg(ctx.payload)
    inputs = {"peg": peg, "earnings_growth": ctx.num("earnings_growth")}
    threshold = "0 < PEG < 1"
    if peg is None:
        checks.append(unknown_check(Axis.VALUE, 5, "peg_below_1", reason,
                                    inputs, threshold, ctx.lineage(*PRICE_FIN)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.VALUE, id=5, name="peg_below_1",
            condition_inputs=inputs, lineage_fields=PRICE_FIN,
            threshold=threshold, passes=0 < peg < 1,
            quality_fields=("price", "eps", "earnings_growth")))

    # V6 PB from tangible book value only
    pb, reason = compute_pb(ctx.payload)
    pb_ind = ctx.nested_num("industry_averages", "pb_average")
    inputs = {"pb_tangible": pb, "industry_pb_average": pb_ind}
    threshold = "0 < PB(tangible) < industry_PB_average"
    if pb is None:
        checks.append(unknown_check(Axis.VALUE, 6, "pb_below_industry", reason,
                                    inputs, threshold, ctx.lineage(*PRICE_IND)))
    elif pb_ind is None:
        checks.append(unknown_check(Axis.VALUE, 6, "pb_below_industry",
                                    ReasonCode.MISSING_INPUT, inputs, threshold,
                                    ctx.lineage(*PRICE_IND)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.VALUE, id=6, name="pb_below_industry",
            condition_inputs=inputs, lineage_fields=PRICE_IND,
            threshold=threshold, passes=0 < pb < pb_ind,
            quality_fields=("price", "total_assets", "intangible_assets",
                            "total_liabilities", "shares_outstanding")))
    return checks
