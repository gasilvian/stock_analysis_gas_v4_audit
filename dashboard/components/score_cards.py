"""Score card helpers."""
from __future__ import annotations

from typing import Any, Dict

from dashboard.streamlit_compat import st


def render_score_cards(scores: Dict[str, Dict[str, Any]]) -> None:
    axes = ["value", "future", "past", "health", "dividend"]
    cols = st.columns(len(axes))
    for col, axis in zip(cols, axes):
        with col:
            sc = scores.get(axis, {})
            st.metric(axis.title(), f"{sc.get('score_raw', 'UNKNOWN')}/6", f"coverage {sc.get('coverage_pct', 0):.0%}" if isinstance(sc.get("coverage_pct"), (int, float)) else "coverage UNKNOWN")
