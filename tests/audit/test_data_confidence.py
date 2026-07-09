import copy
import json
from pathlib import Path

from sws_engine.audit.data_confidence import assess_data_confidence
from sws_engine.audit.missing_inputs import classify_missing_inputs


def _demo_output():
    return json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))


def test_data_confidence_high_medium_low_unknown():
    out = _demo_output()
    high = assess_data_confidence(out)
    assert high["level"] == "HIGH"
    assert high["unknown_checks_count"] == 0

    degraded = copy.deepcopy(out)
    degraded["provider_profile"] = "yfinance_pragmatic"
    degraded["warnings"].append("YFINANCE_PRAGMATIC: degraded provider")
    for idx, check in enumerate(degraded["checks"][:12]):
        if idx < 6:
            check["result"] = "UNKNOWN"
            check["reason_code"] = "MISSING_FCF_ESTIMATES"
            check["source_quality"] = "missing"
        else:
            check["source_quality"] = "approximation"
    medium_or_low = assess_data_confidence(degraded)
    assert medium_or_low["level"] in {"MEDIUM", "LOW"}
    assert medium_or_low["unknown_checks_count"] == 6

    empty = assess_data_confidence({"checks": [], "warnings": []})
    assert empty["level"] == "UNKNOWN"


def test_data_confidence_yfinance_degraded_visible():
    out = _demo_output()
    out["provider_profile"] = "yfinance_pragmatic"
    audit = assess_data_confidence(out)
    assert audit["provider_degradation_visible"] is True
    assert "YFINANCE_PRAGMATIC_DEGRADED" in audit["reason_codes"]
    assert audit["level"] != "HIGH"


def test_critical_missing_inputs_from_unknown_checks():
    out = _demo_output()
    checks = copy.deepcopy(out["checks"])
    checks[0]["result"] = "UNKNOWN"
    checks[0]["reason_code"] = "MISSING_RISK_FREE_RATE_AND_EQUITY_RISK_PREMIUM"
    checks[0]["source_quality"] = "missing"
    checks[0]["inputs"] = {"risk_free_rate_10y_5y_avg": None, "equity_risk_premium": None}
    missing = classify_missing_inputs(checks)
    fields = {m["field"] for m in missing}
    assert "risk_free_rate_10y_5y_avg" in fields
    assert "equity_risk_premium" in fields
