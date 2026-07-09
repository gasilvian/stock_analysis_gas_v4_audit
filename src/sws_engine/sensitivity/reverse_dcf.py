"""Reverse DCF helper.

P0.5 implements the conservative two-stage-FCF fallback case only: it solves
for the base FCF growth rate implied by the current price when adjusted FCF,
shares, discount rate and terminal growth are available. Missing inputs remain
UNKNOWN.
"""
from __future__ import annotations

from typing import Any, Dict

from sws_engine.contracts.input_contract import get_num
from sws_engine.valuation.discount_rate import cost_of_equity
from sws_engine.valuation.two_stage_fcf import adjusted_fcf, two_stage_fcf_value


def reverse_dcf_implied_growth(payload: Dict[str, Any], assumptions: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("fcf_estimates"):
        return {
            "status": "UNKNOWN",
            "reason_code": "REVERSE_DCF_ANALYST_FCF_NOT_IMPLEMENTED",
            "implied_base_growth": None,
        }
    price = get_num(payload, "price")
    shares = get_num(payload, "shares_outstanding")
    discount_rate = get_num(payload, "discount_rate")
    if discount_rate is None:
        discount_rate = cost_of_equity(payload, assumptions)
    terminal_growth = get_num(payload, "long_run_growth")
    if terminal_growth is None:
        terminal_growth = get_num(payload, "risk_free_rate_10y_5y_avg")
    base_fcf = adjusted_fcf(get_num(payload, "operating_cash_flow"), payload.get("capex_history_3y"))
    if None in (price, shares, discount_rate, terminal_growth, base_fcf):
        return {
            "status": "UNKNOWN",
            "reason_code": "REVERSE_DCF_INPUTS_MISSING",
            "implied_base_growth": None,
            "input_lineage": {
                "price": price is not None,
                "shares_outstanding": shares is not None,
                "discount_rate": discount_rate is not None,
                "long_run_growth": terminal_growth is not None,
                "adjusted_fcf": base_fcf is not None,
            },
        }
    if discount_rate <= terminal_growth:
        return {"status": "UNKNOWN", "reason_code": "DISCOUNT_RATE_NOT_ABOVE_TERMINAL_GROWTH", "implied_base_growth": None}
    cfg = policy.get("reverse_dcf", {})
    lo = float(cfg.get("min_growth", -0.20))
    hi = float(cfg.get("max_growth", 0.30))
    tol = float(cfg.get("tolerance", 0.0001))
    max_iter = int(cfg.get("max_iterations", 100))
    decay = float((assumptions.get("dcf_decay_factor") or {}).get("value", 0.7))

    def fv_for_growth(growth: float) -> float | None:
        fv, _ = two_stage_fcf_value(
            base_fcf=base_fcf,
            base_growth=growth,
            discount_rate=discount_rate,
            long_run_growth=terminal_growth,
            decay=decay,
            shares_outstanding=shares,
        )
        return fv

    fv_lo = fv_for_growth(lo)
    fv_hi = fv_for_growth(hi)
    if fv_lo is None or fv_hi is None or not (fv_lo <= price <= fv_hi):
        return {
            "status": "UNKNOWN",
            "reason_code": "REVERSE_DCF_PRICE_OUTSIDE_BRACKET",
            "implied_base_growth": None,
            "bracket": {"min_growth": lo, "max_growth": hi, "fair_value_min": fv_lo, "fair_value_max": fv_hi, "price": price},
        }
    mid = (lo + hi) / 2.0
    fv_mid = fv_for_growth(mid)
    iterations = 0
    for iterations in range(1, max_iter + 1):
        mid = (lo + hi) / 2.0
        fv_mid = fv_for_growth(mid)
        if fv_mid is None:
            break
        if abs(fv_mid - price) <= max(tol * price, tol):
            break
        if fv_mid < price:
            lo = mid
        else:
            hi = mid
    return {
        "status": "PASS",
        "reason_code": "REVERSE_DCF_IMPLIED_GROWTH_COMPUTED",
        "implied_base_growth": mid,
        "fair_value_at_implied_growth": fv_mid,
        "iterations": iterations,
        "bracket": {"min_growth": float(cfg.get("min_growth", -0.20)), "max_growth": float(cfg.get("max_growth", 0.30)), "price": price},
        "source_quality": "approximation",
        "source_class": "E3",
    }
