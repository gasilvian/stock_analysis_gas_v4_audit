"""Portfolio orchestration (SPEC section 8): watchlist/holdings/portfolio
types, returns, FX and Snowflake aggregation in one output dict."""
from sws_engine.portfolio.aggregation import aggregate_snowflake
from sws_engine.portfolio.returns import portfolio_returns

PORTFOLIO_TYPES = ("watchlist", "holdings", "portfolio")


def synthesize_transactions(portfolio_type, positions, valuation_date):
    """Watchlist: synthetic equal-weight buys; Holdings: synthetic buys with
    supplied quantities; Portfolio: transactions supplied per position."""
    if portfolio_type == "portfolio":
        return None  # transactions come with the payload
    txs = {}
    n = max(len(positions), 1)
    for p in positions:
        qty = p.get("quantity") if portfolio_type == "holdings" else None
        price = p.get("current_price")
        if qty is None:
            qty = (1.0 / n) / price if price else None  # equal current weights
        txs[p["ticker"]] = [{"type": "buy", "date": valuation_date,
                             "price": price, "shares": qty}]
    return txs


def run_portfolio_analysis(payload: dict, assumptions: dict) -> dict:
    ptype = payload.get("portfolio_type", "portfolio")
    if ptype not in PORTFOLIO_TYPES:
        raise ValueError(f"portfolio_type must be one of {PORTFOLIO_TYPES}")
    vd = payload["valuation_date"]
    positions = payload.get("positions", [])
    synthetic = synthesize_transactions(ptype, positions, vd)

    per_position = {}
    for p in positions:
        txs = p.get("transactions") if synthetic is None \
            else synthetic.get(p["ticker"])
        if not txs or p.get("current_price") is None:
            per_position[p["ticker"]] = None
            continue
        per_position[p["ticker"]] = portfolio_returns(
            txs, current_price=p["current_price"], valuation_date=vd,
            dividends_not_reinvested=p.get("dividends_not_reinvested", 0.0))

    # current position weights derived from current value (SPEC 8.2);
    # explicit 'weight' on a position overrides the derived value
    total_value = 0.0
    for p in positions:
        r = per_position.get(p["ticker"])
        p["_current_value"] = (r or {}).get("current_value") or (
            (p.get("quantity") or 0) * (p.get("current_price") or 0))
        total_value += p["_current_value"]
    for p in positions:
        if p.get("weight") is None:
            p["weight"] = (p["_current_value"] / total_value
                           if total_value > 0 else 0.0)

    snowflake = aggregate_snowflake(
        [p for p in positions if p.get("scores")], assumptions) \
        if any(p.get("scores") for p in positions) else None

    return {
        "portfolio_type": ptype,
        "valuation_date": vd,
        "returns_per_position": per_position,
        "snowflake": snowflake,
        "warnings": [
            "NOT_INVESTMENT_ADVICE: portfolio analytics based on the public "
            "historical SWS methodology",
        ],
    }
