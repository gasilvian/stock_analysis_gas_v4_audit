"""Portfolio Snowflake aggregation (SPEC 8.1/8.2).

portfolio_axis_score = sum(company_axis_score_raw * current_weight)
contributor_value    = company_axis_score_raw * current_weight
Invariant (tested): contributors per axis sum to the portfolio axis score.

ETFs/funds are excluded from the portfolio Snowflake. Outlier caps
(assumptions.yaml outlier_caps, E3) apply to weighted ratio metrics."""
AXES = ("value", "future", "past", "health", "dividend")


def _cap(value, cap):
    if value is None:
        return None
    return min(value, cap) if cap is not None else value


def aggregate_snowflake(positions, assumptions=None):
    """positions: [{'ticker', 'weight', 'is_etf': bool,
                    'scores': {axis: {'score_raw': int, ...}},
                    'metrics': {'pe':.., 'pb':.., 'peg':..}}]"""
    caps = ((assumptions or {}).get("outlier_caps") or {})
    eligible = [p for p in positions if not p.get("is_etf")]
    total_w = sum(p["weight"] for p in eligible)
    if total_w <= 0:
        return None
    result = {"axes": {}, "contributors": {}, "excluded_etf": [
        p["ticker"] for p in positions if p.get("is_etf")]}
    for axis in AXES:
        contributors = []
        for p in eligible:
            w = p["weight"] / total_w
            raw = p["scores"][axis]["score_raw"]
            contributors.append({"ticker": p["ticker"], "weight": round(w, 6),
                                 "contributor_value": raw * w})
        score = sum(c["contributor_value"] for c in contributors)
        result["axes"][axis] = round(score, 6)
        result["contributors"][axis] = contributors
    metrics = {}
    for m, cap_key in (("pe", "pe_max"), ("pb", "pb_max"), ("peg", "peg_max")):
        vals = [(p["weight"] / total_w, _cap((p.get("metrics") or {}).get(m),
                                             caps.get(cap_key)))
                for p in eligible]
        known = [(w, v) for w, v in vals if v is not None]
        metrics[m] = (sum(w * v for w, v in known) / sum(w for w, _ in known)
                      if known else None)
    result["weighted_metrics"] = metrics
    return result
