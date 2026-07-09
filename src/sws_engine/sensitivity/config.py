"""Sensitivity policy loader.

The sensitivity policy is intentionally separate from config/assumptions.yaml.
It controls audit scenarios only and must not alter base model assumptions.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_POLICY: Dict[str, Any] = {
    "metadata": {"version": "default"},
    "discount_rate_terminal_growth": {
        "discount_rate_bps": [-100, 0, 100],
        "terminal_growth_bps": [-50, 0, 50],
    },
    "valuation_range": {
        "bear": {"discount_rate_bps": 100, "terminal_growth_bps": -50},
        "base": {"discount_rate_bps": 0, "terminal_growth_bps": 0},
        "bull": {"discount_rate_bps": -100, "terminal_growth_bps": 50},
    },
    "erp_sensitivity_bps": [-100, 0, 100],
    "risk_free_sensitivity_bps": [-100, 0, 100],
    "terminal_value_dominance_threshold": 0.75,
    "fragility_thresholds": {
        "medium_spread_pct_of_base": 0.25,
        "high_spread_pct_of_base": 0.60,
    },
    "reverse_dcf": {
        "min_growth": -0.20,
        "max_growth": 0.30,
        "tolerance": 0.0001,
        "max_iterations": 100,
    },
}


def load_sensitivity_policy(path: str | None = None) -> Dict[str, Any]:
    policy = deepcopy(DEFAULT_POLICY)
    if not path:
        return policy
    p = Path(path)
    if not p.exists():
        return policy
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return policy
    return _deep_merge(policy, data)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def bps_to_decimal(value: float | int | None) -> float:
    return float(value or 0) / 10000.0
