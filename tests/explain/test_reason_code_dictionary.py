from sws_engine.core.enums import ReasonCode
from sws_engine.explain.dictionary import REQUIRED_REASON_CODES, load_reason_code_dictionary, validate_reason_code_dictionary


def test_reason_code_dictionary_complete_for_required_codes():
    report = validate_reason_code_dictionary("config/reason_code_dictionary.yaml")
    assert report["status"] == "PASS", report
    assert not report["missing_reason_codes"]
    assert {code.value for code in ReasonCode}.issubset(REQUIRED_REASON_CODES)


def test_reason_code_dictionary_contains_not_investment_advice_metadata():
    dictionary = load_reason_code_dictionary("config/reason_code_dictionary.yaml")
    assert dictionary["metadata"]["not_investment_advice"] is True
    assert dictionary["reason_codes"]["MISSING_INPUT"]["analyst"]
