"""Cash-runway HEALTH variant for loss-making companies (SPEC 5.5):
H1-H4 unchanged; H5/H6 replaced by cash-runway checks.

Loss-making = negative currently AND on average over
loss_making_average_window_years (E2, default 3, assumptions.yaml)."""
from sws_engine.checks._helpers import CheckContext, binary_check
from sws_engine.core.enums import Axis, SourceClass

FIN = ("financials_as_of",)


def is_loss_making(ctx: CheckContext) -> bool:
    window = int((ctx.assumptions.get("loss_making_average_window_years")
                  or {}).get("value", 3))
    cur = ctx.num("current_eps")
    hist = ctx.payload.get("eps_history")
    if cur is None or cur >= 0:
        return False
    if not isinstance(hist, (list, tuple)) or len(hist) < window:
        return True  # currently loss-making, no history to contradict
    recent = [float(v) for v in hist[-window:]]
    return sum(recent) / len(recent) < 0


def runway_checks(ctx: CheckContext):
    cash = ctx.num("cash_and_st_investments")
    burn = ctx.num("annual_free_cash_burn")           # positive number = burn
    burn_growth = ctx.num("cash_burn_growth_3y")      # historical annual rate
    checks = []

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=5, name="cash_covers_stable_burn_1y",
        condition_inputs={"cash_and_st_investments": cash,
                          "annual_free_cash_burn": burn},
        lineage_fields=FIN,
        threshold="cash + ST investments > 1 year stable cash burn",
        passes=cash is not None and burn is not None and cash > burn,
        source_class=SourceClass.E0,
        quality_fields=("cash_and_st_investments", "annual_free_cash_burn")))

    grown = None if burn is None or burn_growth is None \
        else burn * (1 + burn_growth)
    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=6, name="cash_covers_growing_burn_1y",
        condition_inputs={"cash_and_st_investments": cash,
                          "annual_free_cash_burn": burn,
                          "cash_burn_growth_3y": burn_growth,
                          "projected_burn_1y": grown},
        lineage_fields=FIN,
        threshold="cash + ST investments > 1 year burn grown at 3y rate",
        passes=cash is not None and grown is not None and cash > grown,
        source_class=SourceClass.E0,
        quality_fields=("cash_and_st_investments", "annual_free_cash_burn")))
    return checks
