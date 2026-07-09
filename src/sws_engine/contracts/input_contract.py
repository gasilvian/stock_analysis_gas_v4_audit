"""Input normalization per data_contract.md.

STRICT MODE: this contract never invents or autofills missing analytical
inputs. Missing fields stay missing; dependent checks return UNKNOWN.
"""
from sws_engine.core.enums import ProviderProfile

REQUIRED_FIELDS = ("ticker", "exchange", "valuation_date", "provider_profile")


class InputContractError(ValueError):
    pass


def normalize_input(payload: dict) -> dict:
    missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
    if missing:
        raise InputContractError(f"missing required input fields: {missing}")
    ProviderProfile(payload["provider_profile"])  # validate enum
    # shallow copy; do NOT fill defaults for analytical fields (strict mode)
    return dict(payload)


def get_num(payload: dict, field: str):
    """Return numeric value or None. Never substitutes a default."""
    v = payload.get(field)
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None
