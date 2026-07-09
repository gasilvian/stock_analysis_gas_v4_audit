"""Screener page."""
from __future__ import annotations

import pandas as pd

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.footer import render_footer
from dashboard.streamlit_compat import st

AXES = ["value", "future", "past", "health", "dividend"]


def _flatten_row(row: dict, axis: str | None) -> dict:
    scores = row.get("scores", {}) or {}
    selected_axis = axis or (next(iter(scores.keys())) if scores else None)
    score = scores.get(selected_axis, {}) if selected_axis else {}
    return {
        "ticker": row.get("ticker"),
        "exchange": row.get("exchange"),
        "valuation_date": row.get("valuation_date"),
        "provider_profile": row.get("provider_profile"),
        "fair_value": row.get("fair_value"),
        "price": row.get("price"),
        "discount_pct": row.get("discount_pct"),
        "axis": selected_axis,
        "score_raw": score.get("score_raw"),
        "coverage_pct": score.get("coverage_pct"),
        "unknown_checks_count": score.get("unknown_checks_count"),
        "warnings_count": row.get("warnings_count"),
        "run_id": row.get("run_id"),
    }


def main() -> None:
    st.set_page_config(page_title="Screener", layout="wide")
    st.title("Screener")
    client = ApiClient.from_env()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        axis = st.selectbox("Axis", AXES, index=0)
    with c2:
        min_score = int(st.slider("Min score", min_value=0, max_value=6, value=0))
    with c3:
        min_coverage = float(st.slider("Min coverage", min_value=0.0, max_value=1.0, value=0.66))
    with c4:
        provider_profile = st.selectbox("Provider", ["ALL", "sws_public_faithful_manual_inputs", "yfinance_pragmatic"], index=0)
    with c5:
        limit = int(st.number_input("Limit", min_value=1, max_value=500, value=100))
    provider = None if provider_profile == "ALL" else provider_profile
    try:
        response = client.screener(axis=axis, min_score=min_score, min_coverage=min_coverage, provider_profile=provider, limit=limit)
    except ApiClientError as exc:
        st.error(str(exc))
        render_footer()
        return
    rows = (response or {}).get("rows", [])
    flattened = [_flatten_row(row, axis) for row in rows]
    if not flattened:
        st.info("No screener rows match the filters. Persist company outputs first.")
        render_footer()
        return
    df = pd.DataFrame(flattened)
    if "coverage_pct" not in df.columns:
        st.error("Screener response is missing coverage_pct; score-only screener results are not allowed.")
        render_footer()
        return
    df = df[df["coverage_pct"] >= min_coverage]
    df = df.sort_values(by=["coverage_pct", "score_raw", "discount_pct"], ascending=[False, False, False], na_position="last")
    st.dataframe(df, use_container_width=True)
    st.caption("Rows are sorted by coverage_pct, then score_raw, then discount_pct. Scores are never displayed without coverage.")
    render_footer()


if __name__ == "__main__":
    main()
