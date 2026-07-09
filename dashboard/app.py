"""Main Streamlit entry point for the SWS Snowflake Engine dashboard."""
from __future__ import annotations

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.badges import render_badge, render_data_layer_badge, render_validation_badge
from dashboard.components.footer import render_footer
from dashboard.streamlit_compat import st


def main() -> None:
    st.set_page_config(page_title="SWS Snowflake Engine v3.1", layout="wide")
    st.title("SWS Snowflake Engine v3.1 Dashboard")
    st.caption("Internal prototype dashboard over the FastAPI backend. Synthetic/no-network data layer in this build.")

    client = ApiClient.from_env()
    try:
        health = client.get_meta_health() or {}
    except ApiClientError as exc:
        st.error(str(exc))
        health = {}

    st.subheader("API status")
    if health:
        cols = st.columns(4)
        with cols[0]:
            render_badge("Status", health.get("status"))
        with cols[1]:
            render_data_layer_badge(health.get("data_layer"))
        with cols[2]:
            render_badge("Live market data", health.get("live_market_data"))
        with cols[3]:
            render_validation_badge(health.get("validation_status"))
        st.write({
            "engine_version": health.get("engine_version"),
            "api_version": health.get("api_version"),
            "tests_recorded": health.get("tests_recorded"),
            "docs": "/docs",
            "health": "/meta/health",
        })
        if health.get("live_market_data") is False:
            st.warning("This dashboard is running on synthetic/no-network construction data. Do not interpret outputs as real market analysis.")
    else:
        st.warning("API health is unavailable. Start FastAPI with: uvicorn sws_engine.api.app:app --reload")

    st.subheader("Pages")
    st.markdown(
        """
        - **Company View** — Snowflake radar, valuation, checks, warnings, lineage and history.
        - **Portfolio View** — weighted Snowflake, positions and returns.
        - **Screener** — score filters with mandatory coverage visibility.
        - **Run & Data Health** — API/data-layer status.
        - **Assumptions & Governance** — active assumptions and UNKNOWN scoring policy.
        - **Audit Workflow Hub** — API-only workflow status for audit, explanations, sensitivity, business risk, memo and run comparison.
        """
    )
    render_footer()


if __name__ == "__main__":
    main()
