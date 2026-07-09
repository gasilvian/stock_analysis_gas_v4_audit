"""REIT valuation (SPEC 4.1/4.3): AFFO-based 2-stage DCF with documented
fallbacks: AFFO (base) -> FFO (ffo_fallback, E3) -> NAV per share
(nav_fallback, E3). Reuses the two-stage machinery."""
from sws_engine.valuation.two_stage_fcf import two_stage_fcf_value


def affo_dcf_value(*, affo_ffo_nav, discount_rate, long_run_growth, decay,
                   shares_outstanding, base_growth=None):
    data = affo_ffo_nav or {}
    for key, variant in (("affo", "base"), ("ffo", "ffo_fallback")):
        series = data.get(f"{key}_estimates")
        base = data.get(key)
        if series:
            fv, det = two_stage_fcf_value(
                analyst_fcf=series, discount_rate=discount_rate,
                long_run_growth=long_run_growth, decay=decay,
                shares_outstanding=shares_outstanding)
            if fv is not None:
                return fv, variant, det
        if base is not None and base_growth is not None:
            fv, det = two_stage_fcf_value(
                base_fcf=base, base_growth=base_growth,
                discount_rate=discount_rate, long_run_growth=long_run_growth,
                decay=decay, shares_outstanding=shares_outstanding)
            if fv is not None:
                return fv, variant, det
    nav = data.get("nav_per_share")
    if nav is not None:
        return float(nav), "nav_fallback", {"method": "nav_per_share"}
    return None, "unknown", "MISSING_INPUT"
