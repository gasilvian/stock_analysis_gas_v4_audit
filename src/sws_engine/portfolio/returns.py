"""Money-weighted portfolio returns (SPEC 8.3; Portfolio-Analysis-Model
model.markdown; gold AMZN example).

Gain = proceeds_from_sales + current_value + dividends_not_reinvested
       - total_purchased
Total_Return = Gain / Total_Capital_Invested
AYI  = weighted average years invested of each buy contribution
CAGR = (1 + Total_Return)^(1/AYI) - 1 ; not reported if AYI < 1.

Buy duration is measured to valuation_date even for lots later sold
(E1, assumptions.yaml portfolio_buy_duration_policy).
Day count: ACT/365.25 (E3, assumptions.yaml portfolio_day_count)."""
from datetime import date, datetime

DAYS_PER_YEAR = 365.25


def _d(x):
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()


def years_between(d0, d1):
    return (_d(d1) - _d(d0)).days / DAYS_PER_YEAR


def portfolio_returns(transactions, current_price, current_shares_hint=None,
                      valuation_date=None, dividends_not_reinvested=0.0,
                      buy_duration_to_valuation_date=True):
    """transactions: list of {'type': 'buy'|'sell', 'date': 'YYYY-MM-DD',
    'price': float, 'shares': float} in portfolio currency."""
    vd = _d(valuation_date)
    total_bought = 0.0
    proceeds = 0.0
    shares = 0.0
    weighted_years = 0.0
    remaining_lots = []  # (shares, cost_date) for non-valuation-date policy

    for t in sorted(transactions, key=lambda t: _d(t["date"])):
        amt = abs(t["price"] * t["shares"])
        if t["type"].lower() == "buy":
            total_bought += amt
            shares += abs(t["shares"])
            yrs = years_between(t["date"], vd)
            weighted_years += amt * yrs
            remaining_lots.append([abs(t["shares"]), t["date"], t["price"]])
        else:
            proceeds += amt
            shares -= abs(t["shares"])

    if total_bought <= 0:
        return None
    current_value = (current_shares_hint if current_shares_hint is not None
                     else shares) * current_price
    gain = proceeds + current_value + dividends_not_reinvested - total_bought
    total_return = gain / total_bought
    ayi = weighted_years / total_bought
    cagr = None
    if ayi >= 1:
        cagr = (1 + total_return) ** (1 / ayi) - 1
    return {
        "total_purchased": total_bought,
        "proceeds_from_sales": proceeds,
        "current_value": current_value,
        "dividends_not_reinvested": dividends_not_reinvested,
        "gain": gain,
        "total_return": total_return,
        "avg_years_invested": ayi,
        "cagr": cagr,
        "cagr_suppressed_ayi_lt_1": ayi < 1,
        "shares_held": shares,
    }
