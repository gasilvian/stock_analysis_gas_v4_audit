"""Shared regression: Growth = Slope / Mean(abs(values)) (SPEC section 6,
GROWTH.MARKDOWN). Supports equal or analyst-count weighting."""


def slope_mean_growth(values, weights=None):
    """Returns (growth, slope, mean_abs). Growth = slope / mean(|values|).

    Weighted least squares when weights given; mean_abs is always the
    simple mean of absolute values (per public FB example)."""
    n = len(values)
    if n < 2:
        return None, None, None
    xs = list(range(n))
    w = weights if weights is not None else [1.0] * n
    W = sum(w)
    if W <= 0:
        return None, None, None
    xb = sum(wi * xi for wi, xi in zip(w, xs)) / W
    yb = sum(wi * yi for wi, yi in zip(w, values)) / W
    sxx = sum(wi * (xi - xb) ** 2 for wi, xi in zip(w, xs))
    if sxx == 0:
        return None, None, None
    sxy = sum(wi * (xi - xb) * (yi - yb) for wi, xi, yi in zip(w, xs, values))
    slope = sxy / sxx
    mean_abs = sum(abs(v) for v in values) / n
    if mean_abs == 0:
        return None, slope, mean_abs
    return slope / mean_abs, slope, mean_abs
