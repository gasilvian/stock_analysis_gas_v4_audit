"""Growth route C: fundamentals / ROE convergence (SPEC section 6, E1
inference validated on the HemaCare public example).

Rule reproduced from GROWTH.MARKDOWN worked table:
- point 0 = last reported actual earnings;
- equity rolls forward with beginning-of-year equity:
  Equity_START_(t+1) = Equity_START_t + Earnings_t * Retention;
- for t = 1..5, ROE_t is linearly interpolated from current (stable) ROE to
  the industry median ROE over 5 years and applied to beginning equity;
- growth = OLS slope / mean(abs(earnings)) over the 6 points.

Applicability (E0): currently profitable, 0% <= payout < 90%, equity > 0.
Gold: HemaCare 1.85% +/-0.1pp."""
from sws_engine.growth.regression import slope_mean_growth

CONVERGENCE_YEARS = 5


def fundamentals_growth(current_earnings, current_equity, stable_roe,
                        industry_median_roe, payout_ratio):
    if None in (current_earnings, current_equity, stable_roe,
                industry_median_roe, payout_ratio):
        return None
    if current_earnings <= 0 or current_equity <= 0:
        return None
    if not (0 <= payout_ratio < 0.90):
        return None
    retention = 1.0 - payout_ratio
    points = [float(current_earnings)]
    equity_start = current_equity + current_earnings * retention
    for t in range(1, CONVERGENCE_YEARS + 1):
        roe_t = stable_roe + (industry_median_roe - stable_roe) * t / CONVERGENCE_YEARS
        earnings_t = roe_t * equity_start
        points.append(earnings_t)
        equity_start += earnings_t * retention
    growth, _, _ = slope_mean_growth(points)
    return growth


def resolve_growth(payload):
    """Priority A (analyst) -> B (historical) -> C (fundamentals).
    Returns (growth, route) with route in {'analyst','historical','fundamentals',None}."""
    from sws_engine.growth.analyst_regression import analyst_growth
    from sws_engine.growth.historical_regression import historical_growth

    est = payload.get("earnings_estimates")
    g = analyst_growth(payload.get("current_earnings_abs"), est) if est else None
    if g is not None:
        return g, "analyst"
    hist = payload.get("earnings_history")
    g = historical_growth(hist) if hist else None
    if g is not None:
        return g, "historical"
    g = fundamentals_growth(
        payload.get("current_earnings_abs"), payload.get("equity"),
        payload.get("stable_roe"), payload.get("industry_median_roe"),
        payload.get("stable_payout_ratio"))
    if g is not None:
        return g, "fundamentals"
    return None, None
