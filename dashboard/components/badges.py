"""Small badge helpers for dashboard risk/status labeling."""
from __future__ import annotations

from typing import Any

from dashboard.streamlit_compat import st


def badge_kind(value: Any) -> str:
    text = str(value).lower()
    if text in {"pass", "exact", "ok", "sws_public_faithful_manual_inputs", "true"}:
        return "success"
    if text in {"fail", "false"}:
        return "error"
    if text in {"unknown", "missing", "yfinance_pragmatic", "synthetic/no-network"}:
        return "warning"
    if text in {"approximation", "assumption"} or "limitation" in text:
        return "warning"
    return "info"


def render_badge(label: str, value: Any) -> None:
    kind = badge_kind(value)
    text = f"**{label}:** `{value}`"
    if kind == "success":
        st.success(text)
    elif kind == "error":
        st.error(text)
    elif kind == "warning":
        st.warning(text)
    else:
        st.info(text)


def render_provider_badge(provider_profile: str | None) -> None:
    render_badge("Provider", provider_profile or "UNKNOWN")


def render_result_badge(result: str | None) -> None:
    render_badge("Result", result or "UNKNOWN")


def render_source_quality_badge(source_quality: str | None) -> None:
    render_badge("Source quality", source_quality or "missing")


def render_data_layer_badge(data_layer: str | None) -> None:
    render_badge("Data layer", data_layer or "UNKNOWN")


def render_validation_badge(validation_status: str | None) -> None:
    render_badge("Validation", validation_status or "UNKNOWN")
