"""Output lineage contract (data_contract.md / SPEC v3.1 section 2.3)."""

LINEAGE_FIELDS = (
    "price_as_of", "financials_as_of", "analyst_estimates_as_of",
    "fx_as_of", "industry_averages_as_of", "assumptions_as_of",
)


def build_lineage(input_payload: dict, assumptions_meta: dict) -> dict:
    src = input_payload.get("lineage", {}) or {}
    lineage = {f: src.get(f) for f in LINEAGE_FIELDS}
    # assumptions_as_of defaults to the assumptions file review date
    if lineage.get("assumptions_as_of") is None:
        lineage["assumptions_as_of"] = assumptions_meta.get("last_reviewed")
    lineage["provider_versions"] = src.get("provider_versions", {}) or {}
    return lineage


def field_lineage(input_payload: dict, *fields: str) -> dict:
    """Per-check input_lineage: which lineage dates the inputs derive from."""
    src = input_payload.get("lineage", {}) or {}
    return {f: src.get(f) for f in fields}
