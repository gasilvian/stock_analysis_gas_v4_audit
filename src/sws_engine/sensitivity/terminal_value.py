"""Terminal-value dominance helpers."""
from __future__ import annotations

from typing import Any, Dict


def terminal_value_contribution(details: Any, threshold: float = 0.75) -> Dict[str, Any]:
    if not isinstance(details, dict):
        return {
            "status": "UNKNOWN",
            "reason_code": "VALUATION_DETAILS_UNAVAILABLE",
            "terminal_value_pct": None,
            "is_terminal_value_dominated": None,
            "threshold": threshold,
        }
    pv_terminal = details.get("pv_terminal")
    equity_value = details.get("equity_value")
    if equity_value in (None, 0) or pv_terminal is None:
        return {
            "status": "UNKNOWN",
            "reason_code": "TERMINAL_VALUE_INPUTS_MISSING",
            "terminal_value_pct": None,
            "is_terminal_value_dominated": None,
            "threshold": threshold,
        }
    pct = float(pv_terminal) / float(equity_value)
    return {
        "status": "PASS",
        "reason_code": "TERMINAL_VALUE_COMPUTED",
        "terminal_value_pct": pct,
        "is_terminal_value_dominated": pct > threshold,
        "threshold": threshold,
    }
