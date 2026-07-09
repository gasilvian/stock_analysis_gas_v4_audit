"""Assumptions and governance page."""
from __future__ import annotations

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.footer import render_footer
from dashboard.streamlit_compat import st


def main() -> None:
    st.set_page_config(page_title="Assumptions & Governance", layout="wide")
    st.title("Assumptions & Governance")
    client = ApiClient.from_env()
    try:
        assumptions = client.get_assumptions_current() or {}
        health = client.get_meta_health() or {}
    except ApiClientError as exc:
        st.error(str(exc))
        render_footer()
        return
    st.subheader("Assumptions snapshot")
    st.write({
        "assumptions_path": assumptions.get("assumptions_path"),
        "assumptions_hash": assumptions.get("assumptions_hash"),
    })
    st.subheader("Metadata")
    st.json(assumptions.get("metadata", {}))
    st.subheader("UNKNOWN scoring policy")
    policy = assumptions.get("unknown_scoring_policy", {})
    st.json(policy)
    if policy.get("normalize_by_known_checks") is not False:
        st.error("UNKNOWN scoring policy should keep normalize_by_known_checks=false.")
    else:
        st.success("UNKNOWN scoring policy: no implicit normalization.")
    st.subheader("Provider profiles")
    st.json(assumptions.get("provider_profiles", {}))
    raw = assumptions.get("raw", {})
    e_keys = [k for k, v in raw.items() if isinstance(v, dict) and str(v.get("source_class", "")).startswith(("E1", "E2", "E3"))]
    st.subheader("Registered E1/E2/E3 assumptions")
    st.json({key: raw.get(key) for key in e_keys})
    st.subheader("Raw assumptions")
    st.json(raw)
    if health.get("data_layer") == "synthetic/no-network":
        st.warning("Synthetic/no-network data layer is active.")
    render_footer()


if __name__ == "__main__":
    main()
