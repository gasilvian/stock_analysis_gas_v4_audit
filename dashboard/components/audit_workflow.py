"""Dashboard helpers for v4 audit workflow packages."""
from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from dashboard.components.badges import render_badge
from dashboard.streamlit_compat import st


def extract_workflow_rows(package: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not package:
        return []
    rows: list[dict[str, Any]] = []
    for row in package.get("component_status") or []:
        rows.append({
            "component": row.get("component_id"),
            "label": row.get("label"),
            "status": row.get("status"),
            "required": row.get("required"),
            "reason_code": row.get("reason_code"),
            "unknown_indicators_count": row.get("unknown_indicators_count", 0),
            "api_method": row.get("api_method"),
            "api_path": row.get("api_path"),
        })
    return rows


def validate_workflow_package(package: Mapping[str, Any]) -> bool:
    required = [
        "schema_version",
        "status",
        "reason_code",
        "component_status",
        "workflow_steps",
        "readiness_summary",
        "unknown_summary",
        "not_investment_advice",
        "recommendation_language_absent",
    ]
    missing = [key for key in required if key not in package]
    if missing:
        raise ValueError(f"Workflow package missing required fields: {missing}")
    if package.get("schema_version") != "workflow_package.v0.1":
        raise ValueError("Unexpected workflow package schema_version")
    if package.get("not_investment_advice") is not True:
        raise ValueError("Workflow package must carry not_investment_advice=true")
    if package.get("recommendation_language_absent") is not True:
        raise ValueError("Workflow package must not contain recommendation language")
    return True


def workflow_readiness_label(package: Mapping[str, Any] | None) -> str:
    if not package:
        return "UNKNOWN"
    summary = package.get("readiness_summary") or {}
    if summary.get("missing_required_count"):
        return "BLOCKED"
    if summary.get("manual_review_count"):
        return "MANUAL_REVIEW"
    if summary.get("missing_optional_count"):
        return "PARTIAL"
    return "READY"


def render_workflow_package(package: Mapping[str, Any] | None) -> None:
    if not package:
        st.info("No workflow package available.")
        return
    validate_workflow_package(package)
    st.subheader("Audit Workflow Hub")
    cols = st.columns(4)
    readiness = package.get("readiness_summary") or {}
    with cols[0]:
        render_badge("Workflow", workflow_readiness_label(package))
    with cols[1]:
        st.metric("Ready components", readiness.get("ready_count", 0))
    with cols[2]:
        st.metric("Manual review", readiness.get("manual_review_count", 0))
    with cols[3]:
        st.metric("UNKNOWN indicators", readiness.get("total_unknown_indicators", 0))

    rows = extract_workflow_rows(package)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    unknown = package.get("unknown_summary") or {}
    if unknown.get("total_unknown_indicators"):
        st.warning("UNKNOWN remains visible in the workflow package.")
        st.write({
            "components_with_unknown": unknown.get("components_with_unknown", []),
            "critical_missing_inputs_count": unknown.get("critical_missing_inputs_count", 0),
        })

    manual = package.get("manual_review_items") or []
    if manual:
        st.warning(f"Manual review items: {len(manual)}")
        for item in manual[:10]:
            st.write(f"- {item}")

    with st.expander("Workflow package JSON"):
        st.json(package)
