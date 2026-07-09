"""Closed enums per SPEC v3.1 section 2.3 and output_schema.json."""
from enum import Enum


class ProviderProfile(str, Enum):
    SWS_PUBLIC_FAITHFUL_MANUAL_INPUTS = "sws_public_faithful_manual_inputs"
    YFINANCE_PRAGMATIC = "yfinance_pragmatic"


class ValuationModel(str, Enum):
    TWO_STAGE_FCF = "two_stage_fcf"
    DDM = "ddm"
    EXCESS_RETURNS = "excess_returns"
    AFFO_DCF = "affo_dcf"


class ValuationVariant(str, Enum):
    BASE = "base"
    FFO_FALLBACK = "ffo_fallback"
    NAV_FALLBACK = "nav_fallback"
    MANUAL_INPUT = "manual_input"
    UNKNOWN = "unknown"


class CheckResultValue(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ReasonCode(str, Enum):
    OK = "OK"
    MISSING_INPUT = "MISSING_INPUT"
    NEGATIVE_DENOMINATOR = "NEGATIVE_DENOMINATOR"
    PROVIDER_LIMITATION = "PROVIDER_LIMITATION"
    ASSUMPTION_USED = "ASSUMPTION_USED"
    FAIL_BY_DEFAULT = "FAIL_BY_DEFAULT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DIVIDEND_GATE_LOW_YIELD = "DIVIDEND_GATE_LOW_YIELD"


class SourceQuality(str, Enum):
    EXACT = "exact"
    APPROXIMATION = "approximation"
    ASSUMPTION = "assumption"
    MISSING = "missing"


class SourceClass(str, Enum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"


class Axis(str, Enum):
    VALUE = "value"
    FUTURE = "future"
    PAST = "past"
    HEALTH = "health"
    DIVIDEND = "dividend"
    MANAGEMENT = "management"
