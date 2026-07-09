"""Valuation-fragility scoring for sensitivity outputs."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


def fragility_from_values(values: Iterable[Any], base_fair_value: float | None, thresholds: Dict[str, Any]) -> Dict[str, Any]:
    numeric: List[float] = sorted(float(v) for v in values if isinstance(v, (int, float)) and v > 0)
    if base_fair_value in (None, 0) or len(numeric) < 2:
        return {
            "status": "UNKNOWN",
            "reason_code": "INSUFFICIENT_SENSITIVITY_VALUES",
            "fragility_level": "UNKNOWN",
            "spread_pct_of_base": None,
            "values_count": len(numeric),
        }
    p10 = _quantile(numeric, 0.10)
    p90 = _quantile(numeric, 0.90)
    spread = (p90 - p10) / abs(float(base_fair_value))
    medium = float(thresholds.get("medium_spread_pct_of_base", 0.25))
    high = float(thresholds.get("high_spread_pct_of_base", 0.60))
    level = "LOW"
    if spread >= high:
        level = "HIGH"
    elif spread >= medium:
        level = "MEDIUM"
    return {
        "status": "PASS",
        "reason_code": "FRAGILITY_COMPUTED",
        "fragility_level": level,
        "spread_pct_of_base": spread,
        "p10_fair_value": p10,
        "p90_fair_value": p90,
        "values_count": len(numeric),
        "thresholds": {"medium": medium, "high": high},
    }


def _quantile(values: List[float], q: float) -> float:
    if not values:
        raise ValueError("values required")
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] * (1 - frac) + values[hi] * frac
