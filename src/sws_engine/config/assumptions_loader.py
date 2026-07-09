"""Loader for config/assumptions.yaml - the official assumption register
(E1/E2/E3). No silent changes: the loaded snapshot is attached to the run."""
import copy

import yaml

REQUIRED_KEYS = (
    "metadata", "dcf_decay_factor", "ddm_perpetual_growth",
    "excess_returns_expected_growth", "health_no_interest_expense_policy",
    "unknown_scoring_policy", "dividend_gate_policy",
)


class AssumptionsError(ValueError):
    pass


def load_assumptions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise AssumptionsError("assumptions.yaml did not parse to a mapping")
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise AssumptionsError(f"assumptions.yaml missing required keys: {missing}")
    return data


def run_snapshot(assumptions: dict) -> dict:
    """Frozen copy of assumptions used for the run (runbook.md step 1.3)."""
    return copy.deepcopy(assumptions)
