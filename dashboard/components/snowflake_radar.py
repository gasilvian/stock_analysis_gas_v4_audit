"""Snowflake radar chart and score/coverage table."""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go

from dashboard.streamlit_compat import st

AXES = ["value", "future", "past", "health", "dividend"]


def extract_radar_rows(scores: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for axis in AXES:
        if axis not in scores:
            raise ValueError(f"Missing score axis: {axis}")
        score = scores[axis]
        if "coverage_pct" not in score:
            raise ValueError(f"Missing coverage_pct for axis: {axis}")
        rows.append({
            "axis": axis,
            "score_raw": score.get("score_raw"),
            "known_checks_count": score.get("known_checks_count"),
            "unknown_checks_count": score.get("unknown_checks_count"),
            "coverage_pct": score.get("coverage_pct"),
        })
    return rows


def validate_scores_have_coverage(scores: Dict[str, Dict[str, Any]]) -> bool:
    extract_radar_rows(scores)
    return True


def build_radar_figure(scores: Dict[str, Dict[str, Any]]) -> go.Figure:
    rows = extract_radar_rows(scores)
    theta = [r["axis"] for r in rows] + [rows[0]["axis"]]
    r_values = [r["score_raw"] or 0 for r in rows] + [rows[0]["score_raw"] or 0]
    hover = [
        f"{row['axis']}<br>score_raw={row['score_raw']}<br>coverage={row['coverage_pct']:.0%}<br>unknown={row['unknown_checks_count']}"
        for row in rows
    ] + [
        f"{rows[0]['axis']}<br>score_raw={rows[0]['score_raw']}<br>coverage={rows[0]['coverage_pct']:.0%}<br>unknown={rows[0]['unknown_checks_count']}"
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r_values, theta=theta, fill="toself", text=hover, hoverinfo="text", name="score_raw"))
    fig.update_layout(polar={"radialaxis": {"visible": True, "range": [0, 6]}}, showlegend=False, margin={"l": 40, "r": 40, "t": 20, "b": 20})
    return fig


def render_snowflake_radar(scores: Dict[str, Dict[str, Any]]) -> None:
    try:
        rows = extract_radar_rows(scores)
    except ValueError as exc:
        st.error(str(exc))
        return
    fig = build_radar_figure(scores)
    st.plotly_chart(fig, use_container_width=True)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    low = [row for row in rows if row["coverage_pct"] is not None and row["coverage_pct"] < 0.66]
    if low:
        st.warning("One or more axes have coverage below 66%; scores are not directly comparable to high-coverage scores.")
