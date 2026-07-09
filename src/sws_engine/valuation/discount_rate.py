"""Discount rate = Cost of Equity = Rf + levered beta * ERP (SPEC 4.2).
Beta bounded to [0.8, 2.0]. Returns None if inputs are missing (strict mode)."""
from sws_engine.contracts.input_contract import get_num

BETA_MIN, BETA_MAX = 0.8, 2.0


def levered_beta(beta_u_industry, tax_rate, debt_to_equity):
    if beta_u_industry is None or tax_rate is None or debt_to_equity is None:
        return None
    b = beta_u_industry * (1 + (1 - tax_rate) * debt_to_equity)
    return max(BETA_MIN, min(BETA_MAX, b))


def cost_of_equity(payload: dict, assumptions: dict):
    rf = get_num(payload, "risk_free_rate_10y_5y_avg")
    erp = get_num(payload, "equity_risk_premium")
    beta = get_num(payload, "levered_beta")
    if beta is None:
        beta = levered_beta(
            get_num(payload, "beta_u_industry"),
            get_num(payload, "tax_rate")
            if get_num(payload, "tax_rate") is not None
            else (assumptions.get("beta_tax_rate", {}) or {}).get("default_value"),
            get_num(payload, "debt_to_equity"),
        )
    else:
        beta = max(BETA_MIN, min(BETA_MAX, beta))
    if rf is None or erp is None or beta is None:
        return None
    return rf + beta * erp
