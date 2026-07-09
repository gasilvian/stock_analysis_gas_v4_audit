"""Excess Returns for banks/insurance (SPEC 4.5).

Excess_Return  = (Stable_Future_ROE - Cost_of_Equity) * Stable_Future_BVE
Terminal_Value = Excess_Return / (Cost_of_Equity - Expected_Growth_Rate)
Value/share    = (Current_BVE + PV(Terminal_Value)) / Shares

Stable/Future ROE and BVE are consensus or historical-median fallbacks;
this must never degenerate to generic current ROE * BVE (P0 fix).
Expected growth default = 10Y bond 5Y average (E2)."""


def excess_returns_value(*, current_bve, stable_future_roe, stable_future_bve,
                         cost_of_equity, expected_growth, shares_outstanding):
    if None in (current_bve, stable_future_roe, stable_future_bve,
                cost_of_equity, expected_growth) or \
            shares_outstanding in (None, 0):
        return None, "MISSING_INPUT"
    if cost_of_equity <= expected_growth:
        return None, "NEGATIVE_DENOMINATOR"
    excess_return = (stable_future_roe - cost_of_equity) * stable_future_bve
    terminal_value = excess_return / (cost_of_equity - expected_growth)
    fv = (current_bve + terminal_value) / shares_outstanding
    return fv, {"excess_return": excess_return, "terminal_value": terminal_value}
