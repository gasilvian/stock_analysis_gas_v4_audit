"""Two-stage FCF to equity model, 10-year stage 1 (SPEC 4.3;
dcf-update-q1-2019.markdown; gold AMZN FV ~= 1548 +/-0.1%).

- Stage 1: analyst levered-FCF estimates where available; missing years
  extrapolated with r_t - g = decay * (r_(t-1) - g)  (decay is E1,
  assumptions.yaml dcf_decay_factor, calibrated on AMZN).
- Terminal value: Gordon growth at g = 10Y government bond 5Y average.
- End-of-year discounting; FV per share = (PV stage1 + PV TV) / shares.
- If no analyst estimates: base FCF = Adjusted FCF = OCF - 3y avg capex,
  seed growth from the growth engine (route B/C).
Strict mode: returns None when required inputs are missing."""
STAGE1_YEARS = 10


def project_fcf(analyst_fcf, g, decay, seed_growth=None,
                seed_policy="double_decay_from_avg_yoy"):
    """analyst_fcf: ordered list of estimates for years 1..k (k<=10).
    Extrapolates to 10 years. Returns list of 10 FCF values or None.

    Seed policy for the first extrapolated year (E1, calibrated on the AMZN
    public example, which reproduces the documented 14.77%..5.62% growth
    path within 0.05pp):
      first (r - g) = decay^2 * (average analyst YoY growth - g)
    then r_t - g = decay * (r_(t-1) - g) for subsequent years (SPEC 4.3).
    Alternative policy 'single_decay_from_last_yoy' is configurable (E3)."""
    if not analyst_fcf:
        return None
    fcf = [float(v) for v in analyst_fcf][:STAGE1_YEARS]
    if len(fcf) == STAGE1_YEARS:
        return fcf
    if seed_growth is not None:
        base = seed_growth
        first_factor = decay
    elif len(fcf) >= 2:
        yoy = [fcf[i] / fcf[i - 1] - 1 for i in range(1, len(fcf))
               if fcf[i - 1] != 0]
        if not yoy:
            return None
        if seed_policy == "single_decay_from_last_yoy":
            base, first_factor = yoy[-1], decay
        else:  # double_decay_from_avg_yoy (default, AMZN-calibrated E1)
            base, first_factor = sum(yoy) / len(yoy), decay * decay
    else:
        return None
    r = first_factor * (base - g) + g
    fcf.append(fcf[-1] * (1 + r))
    while len(fcf) < STAGE1_YEARS:
        r = decay * (r - g) + g
        fcf.append(fcf[-1] * (1 + r))
    return fcf


def two_stage_fcf_value(*, analyst_fcf=None, base_fcf=None, base_growth=None,
                        discount_rate, long_run_growth, decay,
                        shares_outstanding,
                        seed_policy="double_decay_from_avg_yoy"):
    """Returns (fair_value_per_share, details) or (None, reason)."""
    if discount_rate is None or long_run_growth is None or \
            shares_outstanding in (None, 0):
        return None, "MISSING_INPUT"
    if discount_rate <= long_run_growth:
        return None, "NEGATIVE_DENOMINATOR"
    if analyst_fcf:
        fcf = project_fcf(analyst_fcf, long_run_growth, decay,
                          seed_policy=seed_policy)
    elif base_fcf is not None and base_growth is not None:
        seed = [base_fcf * (1 + base_growth)]
        fcf = project_fcf(seed, long_run_growth, decay, seed_growth=base_growth)
    else:
        return None, "MISSING_INPUT"
    if fcf is None:
        return None, "MISSING_INPUT"
    pv_stage1 = sum(f / (1 + discount_rate) ** (t + 1) for t, f in enumerate(fcf))
    terminal_value = fcf[-1] * (1 + long_run_growth) / (discount_rate - long_run_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** STAGE1_YEARS
    fv = (pv_stage1 + pv_terminal) / shares_outstanding
    return fv, {
        "fcf_projection": fcf,
        "pv_stage1": pv_stage1,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "equity_value": pv_stage1 + pv_terminal,
    }


def adjusted_fcf(operating_cash_flow, capex_history_3y):
    """Adjusted FCF = OCF - 3y average capex (SPEC 4.3)."""
    if operating_cash_flow is None or not capex_history_3y:
        return None
    avg_capex = sum(abs(c) for c in capex_history_3y) / len(capex_history_3y)
    return operating_cash_flow - avg_capex
