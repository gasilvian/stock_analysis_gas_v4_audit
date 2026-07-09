"""MVP valuation: uses a manually supplied fair_value if present
(valuation_variant=manual_input). Never invents a fair value (strict mode);
if fair_value is absent, it stays null and V1/V2 become UNKNOWN."""
from sws_engine.contracts.input_contract import get_num
from sws_engine.core.enums import SourceClass, ValuationVariant


def resolve_fair_value(payload: dict, model: str, variant: str, source_class: str):
    """Returns (fair_value, discount_pct, variant, source_class)."""
    fv = get_num(payload, "fair_value")
    price = get_num(payload, "price")
    if fv is not None:
        variant = ValuationVariant.MANUAL_INPUT.value
        source_class = SourceClass.E3.value
        discount = None
        if price is not None and fv != 0:
            discount = (fv - price) / fv
        return fv, discount, variant, source_class
    # no valuation inputs -> variant unknown (truth table last row, E3)
    return None, None, ValuationVariant.UNKNOWN.value, SourceClass.E3.value
