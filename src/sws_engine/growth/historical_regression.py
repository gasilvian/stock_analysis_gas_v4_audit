"""Growth route B: historical, equally weighted regression, min 3 years
(SPEC section 6; AAPL public example 6.3%)."""
from sws_engine.growth.regression import slope_mean_growth

MIN_YEARS = 3


def historical_growth(values):
    if values is None or len(values) < MIN_YEARS:
        return None
    growth, _, _ = slope_mean_growth([float(v) for v in values])
    return growth
