"""Corporate actions (SPEC 8.4; Portfolio model doc):
- splits/consolidations adjust share counts; fractional results round UP;
- dividend reinvestment converts payments into fractional shares at zero
  cost on the payment date."""
import math


def apply_split(shares, ratio_new, ratio_old=1):
    """e.g. 2-for-1 split: ratio_new=2, ratio_old=1. Fractions round up."""
    if shares is None or not ratio_new or not ratio_old:
        return None
    raw = shares * ratio_new / ratio_old
    return math.ceil(raw) if abs(raw - round(raw)) > 1e-9 else round(raw)


def reinvest_dividend(dividend_amount, price_on_payment_date):
    """Returns fractional shares purchased at zero cost."""
    if dividend_amount is None or not price_on_payment_date:
        return None
    return dividend_amount / price_on_payment_date
