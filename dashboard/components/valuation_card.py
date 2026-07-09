"""Valuation card renderer."""
from __future__ import annotations

from typing import Any, Dict

from dashboard.streamlit_compat import st


def _fmt(value: Any, pct: bool = False) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, (int, float)):
        return f"{value:.1%}" if pct else f"{value:,.4g}"
    return str(value)


def render_valuation_card(output: Dict[str, Any]) -> None:
    st.subheader("Valuation")
    cols = st.columns(3)
    with cols[0]:
        st.metric("Fair value", _fmt(output.get("fair_value")))
    with cols[1]:
        st.metric("Price", _fmt(output.get("price")))
    with cols[2]:
        st.metric("Discount", _fmt(output.get("discount_pct"), pct=True))
    st.write({
        "valuation_model": output.get("valuation_model"),
        "valuation_variant": output.get("valuation_variant"),
        "valuation_model_source_class": output.get("valuation_model_source_class"),
    })
    if output.get("fair_value") is None:
        st.warning("Valuation UNKNOWN: fair_value is null.")
    if output.get("valuation_variant") in {"manual_input", "nav_fallback", "unknown"}:
        st.warning(f"Valuation variant requires interpretation: {output.get('valuation_variant')}")
