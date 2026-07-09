"""DDM (SPEC 4.4): Value = Expected_DPS / (DR - g).
g default = 10Y government bond 5Y average (E2, assumptions.yaml)."""


def ddm_value(expected_dps, discount_rate, perpetual_growth):
    if None in (expected_dps, discount_rate, perpetual_growth):
        return None, "MISSING_INPUT"
    if discount_rate <= perpetual_growth:
        return None, "NEGATIVE_DENOMINATOR"
    return expected_dps / (discount_rate - perpetual_growth), {"g": perpetual_growth}
