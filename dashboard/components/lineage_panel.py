"""Lineage panel renderer."""
from __future__ import annotations

from typing import Any, Dict

from dashboard.streamlit_compat import st

LINEAGE_FIELDS = [
    "price_as_of",
    "financials_as_of",
    "analyst_estimates_as_of",
    "fx_as_of",
    "industry_averages_as_of",
    "assumptions_as_of",
    "provider_versions",
]


def render_lineage_panel(lineage: Dict[str, Any] | None) -> None:
    st.subheader("Lineage")
    if not lineage:
        st.warning("No run-level lineage returned by API.")
        return
    compact = {field: lineage.get(field) for field in LINEAGE_FIELDS}
    st.json(compact)
