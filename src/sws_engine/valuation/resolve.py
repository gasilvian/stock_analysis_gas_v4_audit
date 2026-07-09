"""Valuation resolution (SPEC section 4): applies the model-selection truth
table, then computes fair value with the full engines. Manual fair_value
still takes precedence (manual_input variant). Strict mode: no invented
values; missing inputs -> fair_value null, variant unknown."""
from sws_engine.contracts.input_contract import get_num
from sws_engine.core.enums import SourceClass, ValuationModel, ValuationVariant
from sws_engine.growth.fundamentals import resolve_growth
from sws_engine.valuation.affo_dcf import affo_dcf_value
from sws_engine.valuation.ddm import ddm_value
from sws_engine.valuation.discount_rate import cost_of_equity
from sws_engine.valuation.excess_returns import excess_returns_value
from sws_engine.valuation.model_selection import select_model
from sws_engine.valuation.two_stage_fcf import adjusted_fcf, two_stage_fcf_value


def resolve_valuation(payload: dict, assumptions: dict):
    """Returns (fair_value, discount_pct, model, variant, source_class,
    details, warnings)."""
    warnings = []
    model, variant, mclass = select_model(payload)
    price = get_num(payload, "price")

    manual_fv = get_num(payload, "fair_value")
    if manual_fv is not None:
        return (manual_fv, _disc(manual_fv, price),
                model, ValuationVariant.MANUAL_INPUT.value,
                SourceClass.E3.value, {"method": "manual_input"}, warnings)

    dr = get_num(payload, "discount_rate")
    if dr is None:
        dr = cost_of_equity(payload, assumptions)
    g = get_num(payload, "long_run_growth")
    if g is None:
        g = get_num(payload, "risk_free_rate_10y_5y_avg")  # 10Y bond 5Y avg
    decay = float((assumptions.get("dcf_decay_factor") or {}).get("value", 0.7))

    fv, details = None, None
    if model == ValuationModel.TWO_STAGE_FCF.value:
        est = payload.get("fcf_estimates")
        series = [e["value"] for e in est] if est else None
        if series:
            fv, details = two_stage_fcf_value(
                analyst_fcf=series, discount_rate=dr, long_run_growth=g,
                decay=decay, shares_outstanding=get_num(payload, "shares_outstanding"))
        else:
            base = adjusted_fcf(get_num(payload, "operating_cash_flow"),
                                payload.get("capex_history_3y"))
            growth, route = resolve_growth(payload)
            if base is not None and growth is not None:
                fv, details = two_stage_fcf_value(
                    base_fcf=base, base_growth=growth, discount_rate=dr,
                    long_run_growth=g, decay=decay,
                    shares_outstanding=get_num(payload, "shares_outstanding"))
                if fv is not None:
                    warnings.append(
                        f"ADJUSTED_FCF: no analyst FCF estimates; adjusted FCF "
                        f"(OCF - 3y avg capex) with growth route '{route}'")
    elif model == ValuationModel.EXCESS_RETURNS.value:
        eg = get_num(payload, "excess_returns_expected_growth")
        fv, details = excess_returns_value(
            current_bve=get_num(payload, "current_bve"),
            stable_future_roe=get_num(payload, "stable_future_roe"),
            stable_future_bve=get_num(payload, "stable_future_bve"),
            cost_of_equity=dr, expected_growth=eg if eg is not None else g,
            shares_outstanding=get_num(payload, "shares_outstanding"))
        if fv is not None and eg is None:
            warnings.append("ASSUMPTION_USED: Excess Returns expected growth "
                            "= 10Y bond 5Y average (E2, assumptions.yaml)")
    elif model == ValuationModel.DDM.value:
        pg = get_num(payload, "ddm_perpetual_growth")
        fv, details = ddm_value(get_num(payload, "expected_dps"), dr,
                                pg if pg is not None else g)
        if fv is not None and pg is None:
            warnings.append("ASSUMPTION_USED: DDM perpetual growth = 10Y bond "
                            "5Y average (E2, assumptions.yaml)")
    elif model == ValuationModel.AFFO_DCF.value:
        growth, _ = resolve_growth(payload)
        fv, affo_variant, details = affo_dcf_value(
            affo_ffo_nav=payload.get("affo_ffo_nav"), discount_rate=dr,
            long_run_growth=g, decay=decay,
            shares_outstanding=get_num(payload, "shares_outstanding"),
            base_growth=growth)
        if fv is not None:
            variant = affo_variant
            if affo_variant != "base":
                mclass = SourceClass.E3.value

    if fv is None:
        return (None, None, model, ValuationVariant.UNKNOWN.value,
                SourceClass.E3.value, None, warnings)
    return fv, _disc(fv, price), model, variant, mclass, details, warnings


def _disc(fv, price):
    if fv in (None, 0) or price is None:
        return None
    return (fv - price) / fv
