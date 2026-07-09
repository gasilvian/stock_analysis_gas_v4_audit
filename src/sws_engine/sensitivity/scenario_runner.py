"""Scenario runner for v4.0 P0.5 sensitivity.

This module calls the existing valuation resolver on copied payloads. It never
mutates assumptions.yaml and never changes valuation/check/growth code.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from sws_engine.config.assumptions_loader import load_assumptions
from sws_engine.contracts.input_contract import get_num
from sws_engine.sensitivity.config import bps_to_decimal, load_sensitivity_policy
from sws_engine.sensitivity.fragility import fragility_from_values
from sws_engine.sensitivity.reverse_dcf import reverse_dcf_implied_growth
from sws_engine.sensitivity.terminal_value import terminal_value_contribution
from sws_engine.valuation.discount_rate import cost_of_equity
from sws_engine.valuation.resolve import resolve_valuation


def run_sensitivity(
    payload: Dict[str, Any],
    assumptions: Dict[str, Any] | str,
    *,
    policy_path: str | None = "config/sensitivity.yaml",
    run_id: str | None = None,
    base_output: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    assumptions_obj = load_assumptions(assumptions) if isinstance(assumptions, str) else assumptions
    policy = load_sensitivity_policy(policy_path)
    ticker = payload.get("ticker") or (base_output or {}).get("ticker") or "UNKNOWN"
    valuation_date = payload.get("valuation_date") or (base_output or {}).get("valuation_date")

    base_case = _valuation_case(payload, assumptions_obj)
    warnings: list[str] = []
    if base_case.get("valuation_variant") == "manual_input":
        summary = _unavailable_summary(
            ticker,
            valuation_date,
            run_id,
            "SENSITIVITY_UNAVAILABLE_FOR_MANUAL_FAIR_VALUE",
            payload,
            base_output,
            policy,
        )
        summary["base_case"] = base_case
        return summary
    if base_case.get("fair_value") is None:
        summary = _unavailable_summary(
            ticker,
            valuation_date,
            run_id,
            "BASE_VALUATION_UNKNOWN",
            payload,
            base_output,
            policy,
        )
        summary["base_case"] = base_case
        return summary

    base_dr = _base_discount_rate(payload, assumptions_obj)
    base_g = _base_terminal_growth(payload)
    if base_dr is None or base_g is None:
        summary = _unavailable_summary(
            ticker,
            valuation_date,
            run_id,
            "SENSITIVITY_DRIVER_INPUTS_MISSING",
            payload,
            base_output,
            policy,
        )
        summary["base_case"] = base_case
        return summary

    grid = _scenario_matrix(payload, assumptions_obj, policy, base_dr=base_dr, base_g=base_g)
    range_cases = _valuation_range(payload, assumptions_obj, policy, base_dr=base_dr, base_g=base_g)
    fv_values = [row.get("fair_value") for row in grid] + [case.get("fair_value") for case in range_cases.values()]
    terminal = terminal_value_contribution(base_case.get("details"), float(policy.get("terminal_value_dominance_threshold", 0.75)))
    if terminal.get("is_terminal_value_dominated"):
        warnings.append("TV_DOMINATED: terminal value contribution exceeds configured threshold")
    reverse = reverse_dcf_implied_growth(payload, assumptions_obj, policy)
    fragility = fragility_from_values(fv_values, base_case.get("fair_value"), policy.get("fragility_thresholds", {}))
    if fragility.get("fragility_level") == "HIGH":
        warnings.append("VALUATION_FRAGILITY_HIGH: fair value range is highly sensitive to assumptions")

    status = "PASS" if not warnings else "PASS_WITH_LIMITATIONS"
    return {
        "ticker": ticker,
        "valuation_date": valuation_date,
        "run_id": run_id,
        "status": status,
        "reason_code": "SENSITIVITY_COMPUTED",
        "source_quality": "approximation",
        "source_class": "E3",
        "input_lineage": _input_lineage(payload, base_output, policy, base_dr, base_g),
        "base_case": _public_case(base_case),
        "valuation_range": range_cases,
        "scenario_matrix": grid,
        "terminal_value_contribution": terminal,
        "reverse_dcf": reverse,
        "fragility": fragility,
        "warnings": warnings,
        "not_investment_advice": True,
    }


def _valuation_case(payload: Dict[str, Any], assumptions: Dict[str, Any]) -> Dict[str, Any]:
    fv, discount_pct, model, variant, source_class, details, warnings = resolve_valuation(deepcopy(payload), assumptions)
    return {
        "fair_value": fv,
        "discount_pct": discount_pct,
        "valuation_model": model,
        "valuation_variant": variant,
        "valuation_model_source_class": source_class,
        "details": details,
        "warnings": warnings,
    }


def _public_case(case: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(case)
    details = out.get("details")
    if isinstance(details, dict) and "fcf_projection" in details:
        # Keep the public summary compact. Full output is not necessary to show
        # scenario sensitivity and can be regenerated deterministically.
        out["details"] = {k: v for k, v in details.items() if k != "fcf_projection"}
        out["projection_years"] = len(details.get("fcf_projection") or [])
    return out


def _base_discount_rate(payload: Dict[str, Any], assumptions: Dict[str, Any]) -> float | None:
    return get_num(payload, "discount_rate") or cost_of_equity(payload, assumptions)


def _base_terminal_growth(payload: Dict[str, Any]) -> float | None:
    return get_num(payload, "long_run_growth") or get_num(payload, "risk_free_rate_10y_5y_avg")


def _scenario_matrix(payload: Dict[str, Any], assumptions: Dict[str, Any], policy: Dict[str, Any], *, base_dr: float, base_g: float) -> List[Dict[str, Any]]:
    cfg = policy.get("discount_rate_terminal_growth", {})
    dr_bps = cfg.get("discount_rate_bps", [-100, 0, 100])
    g_bps = cfg.get("terminal_growth_bps", [-50, 0, 50])
    rows: list[dict[str, Any]] = []
    for dr_delta in dr_bps:
        for g_delta in g_bps:
            dr = base_dr + bps_to_decimal(dr_delta)
            g = base_g + bps_to_decimal(g_delta)
            case = _scenario_case(payload, assumptions, dr=dr, g=g)
            rows.append({
                "scenario_type": "discount_rate_x_terminal_growth",
                "discount_rate_bps_delta": int(dr_delta),
                "terminal_growth_bps_delta": int(g_delta),
                "discount_rate": dr,
                "terminal_growth": g,
                **case,
            })
    return rows


def _valuation_range(payload: Dict[str, Any], assumptions: Dict[str, Any], policy: Dict[str, Any], *, base_dr: float, base_g: float) -> Dict[str, Any]:
    out: dict[str, Any] = {}
    for label, cfg in (policy.get("valuation_range") or {}).items():
        dr = base_dr + bps_to_decimal(cfg.get("discount_rate_bps", 0))
        g = base_g + bps_to_decimal(cfg.get("terminal_growth_bps", 0))
        out[label] = {
            "discount_rate": dr,
            "terminal_growth": g,
            "discount_rate_bps_delta": int(cfg.get("discount_rate_bps", 0)),
            "terminal_growth_bps_delta": int(cfg.get("terminal_growth_bps", 0)),
            **_scenario_case(payload, assumptions, dr=dr, g=g),
        }
    return out


def _scenario_case(payload: Dict[str, Any], assumptions: Dict[str, Any], *, dr: float, g: float) -> Dict[str, Any]:
    if dr <= g:
        return {
            "status": "UNKNOWN",
            "reason_code": "DISCOUNT_RATE_NOT_ABOVE_TERMINAL_GROWTH",
            "fair_value": None,
            "discount_pct": None,
        }
    p = deepcopy(payload)
    p["discount_rate"] = dr
    p["long_run_growth"] = g
    # Fair value manual input would suppress model sensitivity; remove nothing
    # here because the caller already blocks manual-fair-value base cases.
    fv, discount_pct, model, variant, source_class, _details, warnings = resolve_valuation(p, assumptions)
    return {
        "status": "PASS" if fv is not None else "UNKNOWN",
        "reason_code": "SCENARIO_COMPUTED" if fv is not None else "SCENARIO_VALUATION_UNKNOWN",
        "fair_value": fv,
        "discount_pct": discount_pct,
        "valuation_model": model,
        "valuation_variant": variant,
        "valuation_model_source_class": source_class,
        "warnings": warnings,
    }


def _input_lineage(payload: Dict[str, Any], base_output: Dict[str, Any] | None, policy: Dict[str, Any], base_dr: float | None, base_g: float | None) -> Dict[str, Any]:
    return {
        "provider_profile": payload.get("provider_profile") or (base_output or {}).get("provider_profile"),
        "valuation_model": (base_output or {}).get("valuation_model"),
        "valuation_variant": (base_output or {}).get("valuation_variant"),
        "base_discount_rate": base_dr,
        "base_terminal_growth": base_g,
        "sensitivity_policy_version": (policy.get("metadata") or {}).get("version"),
        "source_quality": "approximation",
        "source_class": "E3",
    }


def _unavailable_summary(
    ticker: str,
    valuation_date: str | None,
    run_id: str | None,
    reason_code: str,
    payload: Dict[str, Any],
    base_output: Dict[str, Any] | None,
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "valuation_date": valuation_date,
        "run_id": run_id,
        "status": "UNKNOWN",
        "reason_code": reason_code,
        "source_quality": "missing",
        "source_class": "E3",
        "input_lineage": _input_lineage(payload, base_output, policy, None, None),
        "base_case": {},
        "valuation_range": {},
        "scenario_matrix": [],
        "terminal_value_contribution": {"status": "UNKNOWN", "reason_code": "SENSITIVITY_UNAVAILABLE"},
        "reverse_dcf": {"status": "UNKNOWN", "reason_code": "SENSITIVITY_UNAVAILABLE"},
        "fragility": {"status": "UNKNOWN", "reason_code": "SENSITIVITY_UNAVAILABLE", "fragility_level": "UNKNOWN"},
        "warnings": [reason_code],
        "not_investment_advice": True,
    }
