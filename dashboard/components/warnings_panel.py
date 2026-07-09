"""Warnings panel with explicit model-risk visibility."""
from __future__ import annotations

from typing import Iterable, List

from dashboard.streamlit_compat import st

IMPORTANT_WARNING_TOKENS = (
    "PROVIDER_LIMITATION",
    "DEMO_FIXTURE_ONLY",
    "SYNTHETIC_CURATED_DATA",
    "ASSUMPTION_USED",
    "NOT_INVESTMENT_ADVICE",
    "LIVE_YFINANCE_PRAGMATIC",
)


def classify_warning(warning: str) -> str:
    text = warning.upper()
    if any(token in text for token in IMPORTANT_WARNING_TOKENS):
        return "important"
    if "UNKNOWN" in text or "COVERAGE" in text:
        return "coverage"
    return "general"


def has_important_warnings(warnings: Iterable[str]) -> bool:
    return any(classify_warning(w) == "important" for w in warnings)


def important_warnings(warnings: Iterable[str]) -> bool:
    """Backward-compatible alias used by dashboard tests."""
    return has_important_warnings(warnings)


def render_warnings(warnings: Iterable[str] | None) -> None:
    warnings_list: List[str] = list(warnings or [])
    st.subheader("Warnings")
    if not warnings_list:
        st.success("No warnings returned by API.")
        return
    if has_important_warnings(warnings_list):
        st.warning("Important provider/data/model-risk warnings are present and must be reviewed.")
    for item in warnings_list:
        if classify_warning(item) == "important":
            st.warning(item)
        else:
            st.info(item)
