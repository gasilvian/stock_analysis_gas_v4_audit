"""Checks table renderer and contract validator."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

import pandas as pd

from dashboard.streamlit_compat import st

REQUIRED_CHECK_FIELDS = [
    "axis",
    "id",
    "name",
    "result",
    "reason_code",
    "source_quality",
    "source_class",
    "inputs",
    "threshold",
    "input_lineage",
]


def validate_check_contract(check: Dict[str, Any]) -> bool:
    missing = [field for field in REQUIRED_CHECK_FIELDS if field not in check]
    if missing:
        raise ValueError(f"Check contract missing fields: {missing}")
    return True


def validate_checks_contract(checks: Iterable[Dict[str, Any]]) -> bool:
    for check in checks:
        validate_check_contract(check)
    return True


def checks_to_dataframe(checks: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    checks_list = list(checks or [])
    validate_checks_contract(checks_list)
    rows: List[Dict[str, Any]] = []
    for check in checks_list:
        rows.append({
            "axis": check.get("axis"),
            "id": check.get("id"),
            "name": check.get("name"),
            "result": check.get("result"),
            "reason_code": check.get("reason_code"),
            "source_quality": check.get("source_quality"),
            "source_class": check.get("source_class"),
            "threshold": check.get("threshold"),
        })
    return pd.DataFrame(rows)


def render_checks_table(checks: Iterable[Dict[str, Any]] | None) -> None:
    checks_list = list(checks or [])
    st.subheader("Checks")
    if not checks_list:
        st.warning("No checks returned by API.")
        return
    try:
        df = checks_to_dataframe(checks_list)
    except ValueError as exc:
        st.error(str(exc))
        return

    axis_options = ["ALL"] + sorted(df["axis"].dropna().unique().tolist())
    result_options = ["ALL"] + sorted(df["result"].dropna().unique().tolist())
    reason_options = ["ALL"] + sorted(df["reason_code"].dropna().unique().tolist())
    quality_options = ["ALL"] + sorted(df["source_quality"].dropna().unique().tolist())
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        axis = st.selectbox("Axis", axis_options)
    with c2:
        result = st.selectbox("Result", result_options)
    with c3:
        reason = st.selectbox("Reason", reason_options)
    with c4:
        quality = st.selectbox("Source quality", quality_options)

    filtered = df.copy()
    if axis != "ALL":
        filtered = filtered[filtered["axis"] == axis]
    if result != "ALL":
        filtered = filtered[filtered["result"] == result]
    if reason != "ALL":
        filtered = filtered[filtered["reason_code"] == reason]
    if quality != "ALL":
        filtered = filtered[filtered["source_quality"] == quality]
    st.dataframe(filtered, use_container_width=True)

    names = [f"{c.get('axis')} {c.get('id')} - {c.get('name')}" for c in checks_list]
    selected = st.selectbox("Inspect check inputs and lineage", ["None"] + names)
    if selected != "None":
        idx = names.index(selected)
        check = checks_list[idx]
        with st.expander("inputs", expanded=True):
            st.json(check.get("inputs", {}))
        with st.expander("input_lineage", expanded=True):
            st.json(check.get("input_lineage", {}))
