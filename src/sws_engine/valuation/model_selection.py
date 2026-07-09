"""Model-selection truth table (SPEC v3.1 section 4.1)."""
from sws_engine.core.enums import SourceClass, ValuationModel, ValuationVariant


def select_model(payload: dict) -> tuple:
    """Returns (valuation_model, valuation_variant, source_class).

    Company type comes from payload['company_type']:
    non_financial | bank | insurance | reit | other_financial.
    Variant may later be overridden to manual_input/unknown by the
    valuation step depending on available inputs.
    """
    ctype = (payload.get("company_type") or "non_financial").lower()

    if ctype in ("bank", "insurance"):
        if payload.get("bank_deposits_npl_chargeoffs") or payload.get(
                "stable_future_roe") is not None:
            return (ValuationModel.EXCESS_RETURNS.value,
                    ValuationVariant.BASE.value, SourceClass.E0.value)
        return (ValuationModel.DDM.value, ValuationVariant.BASE.value,
                SourceClass.E0.value)

    if ctype == "reit":
        affo = (payload.get("affo_ffo_nav") or {})
        if affo.get("affo") is not None:
            return (ValuationModel.AFFO_DCF.value,
                    ValuationVariant.BASE.value, SourceClass.E0.value)
        if affo.get("ffo") is not None:
            return (ValuationModel.AFFO_DCF.value,
                    ValuationVariant.FFO_FALLBACK.value, SourceClass.E3.value)
        if affo.get("nav") is not None:
            return (ValuationModel.AFFO_DCF.value,
                    ValuationVariant.NAV_FALLBACK.value, SourceClass.E3.value)
        return (ValuationModel.AFFO_DCF.value,
                ValuationVariant.UNKNOWN.value, SourceClass.E3.value)

    if ctype == "other_financial":
        return (ValuationModel.DDM.value, ValuationVariant.BASE.value,
                SourceClass.E0.value)

    # non-financial default
    return (ValuationModel.TWO_STAGE_FCF.value, ValuationVariant.BASE.value,
            SourceClass.E0.value)
