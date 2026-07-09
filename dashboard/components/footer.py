"""Persistent dashboard footer and disclaimer."""
from __future__ import annotations

from dashboard.streamlit_compat import st

DISCLAIMER = "Quantitative exploratory analysis of a public historical methodology. Not investment advice. Not the live Simply Wall St model."
ATTRIBUTION = "Derived from public Simply Wall St GitHub methodology; use subject to NOTICE/license notes."


def render_footer() -> None:
    st.divider()
    st.caption(DISCLAIMER)
    st.caption(ATTRIBUTION)
