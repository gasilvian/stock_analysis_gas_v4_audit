"""Growth route A: analyst estimates, weighted regression (SPEC section 6).

- first data point = most recent actual, weight 1 (GROWTH.MARKDOWN, FB example)
- weight per forecast year = analyst count, capped at 50
- horizon up to 5 forward years
Gold: FB 19.3% +/-0.5pp (public inputs are rounded)."""
from sws_engine.growth.regression import slope_mean_growth

ANALYST_CAP = 50
MAX_HORIZON_YEARS = 5


def analyst_growth(actual_value, estimates):
    """estimates: list of {'value': float, 'analysts': int} ordered by year."""
    if actual_value is None or not estimates:
        return None
    est = estimates[:MAX_HORIZON_YEARS]
    values = [float(actual_value)] + [float(e["value"]) for e in est]
    weights = [1.0] + [min(float(e.get("analysts", 1)), ANALYST_CAP)
                       for e in est]
    growth, _, _ = slope_mean_growth(values, weights)
    return growth
