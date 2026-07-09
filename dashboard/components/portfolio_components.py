"""Portfolio dashboard components."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pandas as pd

from dashboard.streamlit_compat import st


def _as_df(value: Any) -> pd.DataFrame:
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        return pd.DataFrame([value])
    return pd.DataFrame()


def render_portfolio_weighted_scores(output: Dict[str, Any]) -> None:
    st.subheader("Portfolio Snowflake (weighted)")
    scores = output.get("portfolio_scores") or output.get("scores") or output.get("axis_scores") or {}
    if isinstance(scores, dict):
        rows = []
        for axis, value in scores.items():
            rows.append({"axis": axis, "score": value.get("score_raw", value) if isinstance(value, dict) else value})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.json(scores)


def render_returns_table(output: Dict[str, Any]) -> None:
    st.subheader("Returns")
    positions = output.get("positions") or output.get("position_returns") or output.get("returns_per_position") or []
    df = _as_df(positions)
    if df.empty:
        st.info("No per-position returns found in portfolio output.")
    else:
        st.dataframe(df, use_container_width=True)
    summary = {key: output.get(key) for key in ["total_return", "gain", "ayi", "cagr", "valuation_date"] if key in output}
    if summary:
        st.json(summary)


def render_contributors_table(output: Dict[str, Any]) -> None:
    contributors = output.get("contributors") or output.get("axis_contributors") or output.get("contributor_values")
    if not contributors:
        return
    st.subheader("Axis contributors")
    df = _as_df(contributors)
    st.dataframe(df, use_container_width=True)
    st.caption("Invariant to inspect: sum(contributors per axis) = portfolio_axis_score.")
