"""FX conversion and price-vs-currency gain split (SPEC 8.4; gold FX example:
buy $1,000 @1.4 = EUR 1,400; now $1,200 @1.5 = EUR 1,800;
combined gain EUR 400 = price gain EUR 300 (at current FX) + FX gain EUR 100)."""


def convert(amount, fx_rate):
    if amount is None or fx_rate is None:
        return None
    return amount * fx_rate


def gain_split(cost_local, value_local, fx_at_buy, fx_current):
    """All 'local' amounts in the security currency; returns portfolio-currency
    split: combined, price gain (at current FX), net currency gain."""
    if None in (cost_local, value_local, fx_at_buy, fx_current):
        return None
    cost_pc = cost_local * fx_at_buy
    value_pc = value_local * fx_current
    combined_gain = value_pc - cost_pc
    price_gain_local = value_local - cost_local
    price_gain_pc = price_gain_local * fx_current
    currency_gain = combined_gain - price_gain_pc
    return {
        "cost_portfolio_ccy": cost_pc,
        "value_portfolio_ccy": value_pc,
        "combined_gain": combined_gain,
        "price_gain_portfolio_ccy": price_gain_pc,
        "currency_gain": currency_gain,
    }
