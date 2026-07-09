import json

from sws_engine.config.assumptions_loader import load_assumptions
from sws_engine.sensitivity.scenario_runner import run_sensitivity
from sws_engine.sensitivity.terminal_value import terminal_value_contribution


def _payload():
    with open("tests/fixtures/sensitivity/fcf_payload.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_sensitivity_computes_range_matrix_and_fragility():
    summary = run_sensitivity(_payload(), load_assumptions("config/assumptions.yaml"), policy_path="config/sensitivity.yaml")

    assert summary["status"] in {"PASS", "PASS_WITH_LIMITATIONS"}
    assert summary["reason_code"] == "SENSITIVITY_COMPUTED"
    assert summary["source_quality"] == "approximation"
    assert summary["source_class"] == "E3"
    assert set(summary["valuation_range"]) == {"bear", "base", "bull"}
    assert len(summary["scenario_matrix"]) == 9
    assert summary["base_case"]["valuation_model"] == "two_stage_fcf"
    assert summary["fragility"]["fragility_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert summary["not_investment_advice"] is True


def test_reverse_dcf_solves_implied_growth_for_fcf_fallback():
    summary = run_sensitivity(_payload(), load_assumptions("config/assumptions.yaml"), policy_path="config/sensitivity.yaml")

    reverse = summary["reverse_dcf"]
    assert reverse["status"] == "PASS"
    assert reverse["reason_code"] == "REVERSE_DCF_IMPLIED_GROWTH_COMPUTED"
    assert reverse["implied_base_growth"] is not None
    assert abs(reverse["fair_value_at_implied_growth"] - _payload()["price"]) < 0.05


def test_terminal_value_contribution_unknown_without_details():
    result = terminal_value_contribution(None)

    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "VALUATION_DETAILS_UNAVAILABLE"


def test_sensitivity_unavailable_for_manual_fair_value():
    payload = _payload()
    payload["fair_value"] = 120.0
    summary = run_sensitivity(payload, load_assumptions("config/assumptions.yaml"), policy_path="config/sensitivity.yaml")

    assert summary["status"] == "UNKNOWN"
    assert summary["reason_code"] == "SENSITIVITY_UNAVAILABLE_FOR_MANUAL_FAIR_VALUE"
    assert summary["scenario_matrix"] == []
