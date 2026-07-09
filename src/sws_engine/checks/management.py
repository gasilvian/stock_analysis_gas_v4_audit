"""Management module (SPEC section 9; MODEL.markdown). Optional: flags are
informational and NEVER enter Snowflake scores. Emitted only when the
payload sets include_management=true."""
from sws_engine.checks._helpers import CheckContext, binary_check

EST = ("financials_as_of",)


def run(ctx: CheckContext):
    m = ctx.payload.get("management") or {}

    def g(k):
        v = m.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    flags = []
    comp, cohort = g("ceo_total_compensation"), g("ceo_comp_cohort_median")
    flags.append(binary_check(
        ctx, axis="management", id="M1", name="ceo_comp_above_size_cohort",
        condition_inputs={"ceo_total_compensation": comp,
                          "cohort_median": cohort},
        lineage_fields=EST, threshold="CEO comp > size-cohort median (flag)",
        passes=comp is not None and cohort is not None and comp > cohort,
        quality_fields=("management",)))

    pay_up, eps_down = m.get("ceo_pay_rising"), m.get("eps_falling")
    flags.append(binary_check(
        ctx, axis="management", id="M2", name="ceo_pay_up_while_eps_down",
        condition_inputs={"ceo_pay_rising": pay_up, "eps_falling": eps_down},
        lineage_fields=EST, threshold="CEO pay rising while EPS falls (flag)",
        passes=bool(pay_up) and bool(eps_down)
        if pay_up is not None and eps_down is not None else False,
        quality_fields=("management",)))

    mt = g("management_avg_tenure_years")
    flags.append(binary_check(
        ctx, axis="management", id="M3", name="management_tenure_below_2y",
        condition_inputs={"management_avg_tenure_years": mt},
        lineage_fields=EST, threshold="management average tenure < 2 years (flag)",
        passes=mt is not None and mt < 2, quality_fields=("management",)))

    bt = g("board_avg_tenure_years")
    flags.append(binary_check(
        ctx, axis="management", id="M4", name="board_tenure_below_3y",
        condition_inputs={"board_avg_tenure_years": bt},
        lineage_fields=EST, threshold="board average tenure < 3 years (flag)",
        passes=bt is not None and bt < 3, quality_fields=("management",)))

    sold, bought = g("insider_shares_sold_12m"), g("insider_shares_bought_12m")
    flags.append(binary_check(
        ctx, axis="management", id="M5", name="insiders_net_sellers_12m",
        condition_inputs={"insider_shares_sold_12m": sold,
                          "insider_shares_bought_12m": bought},
        lineage_fields=EST, threshold="insider net selling over 12 months (flag)",
        passes=sold is not None and bought is not None and sold > bought,
        quality_fields=("management",)))
    return flags
