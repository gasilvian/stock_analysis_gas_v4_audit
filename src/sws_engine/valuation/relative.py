"""Relative valuation (SPEC v3.1 section 4.6).

PB is strictly tangible-book-value based. Generic bookValuePerShare must
never be used as an exact PB input (risk_register.md)."""
from sws_engine.contracts.input_contract import get_num


def compute_pe(payload: dict):
    price = get_num(payload, "price")
    eps = get_num(payload, "eps")
    if price is None or eps is None:
        return None, "MISSING_INPUT"
    if eps <= 0:
        return None, "NEGATIVE_DENOMINATOR"
    return price / eps, "OK"


def compute_peg(payload: dict):
    pe, pe_reason = compute_pe(payload)
    growth = get_num(payload, "earnings_growth")  # fraction, e.g. 0.15
    if pe is None:
        return None, pe_reason
    if growth is None:
        return None, "MISSING_INPUT"
    growth_pct = growth * 100.0
    if growth_pct <= 0:
        return None, "NEGATIVE_DENOMINATOR"
    return pe / growth_pct, "OK"


def tangible_book_value_per_share(payload: dict):
    ta = get_num(payload, "total_assets")
    ia = get_num(payload, "intangible_assets")
    tl = get_num(payload, "total_liabilities")
    sh = get_num(payload, "shares_outstanding")
    if ta is None or ia is None or tl is None or sh is None:
        return None, "MISSING_INPUT"
    if sh <= 0:
        return None, "NEGATIVE_DENOMINATOR"
    tbv = ta - ia - tl
    return tbv / sh, "OK"


def compute_pb(payload: dict):
    price = get_num(payload, "price")
    tbvps, reason = tangible_book_value_per_share(payload)
    if price is None:
        return None, "MISSING_INPUT"
    if tbvps is None:
        return None, reason
    if tbvps <= 0:
        return None, "NEGATIVE_DENOMINATOR"
    return price / tbvps, "OK"
