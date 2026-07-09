"""Run and data health page."""
from __future__ import annotations

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.badges import render_badge, render_data_layer_badge, render_validation_badge
from dashboard.components.footer import render_footer
from dashboard.streamlit_compat import st


def main() -> None:
    st.set_page_config(page_title="Run & Data Health", layout="wide")
    st.title("Run & Data Health")
    client = ApiClient.from_env()
    try:
        health = client.get_meta_health() or {}
        root = client.get_root() or {}
    except ApiClientError as exc:
        st.error(str(exc))
        render_footer()
        return
    cols = st.columns(4)
    with cols[0]:
        render_badge("Status", health.get("status"))
    with cols[1]:
        render_data_layer_badge(health.get("data_layer"))
    with cols[2]:
        render_badge("Live market data", health.get("live_market_data"))
    with cols[3]:
        render_validation_badge(health.get("validation_status"))
    st.json({
        "engine_version": health.get("engine_version"),
        "api_version": health.get("api_version"),
        "db_path": health.get("db_path"),
        "output_schema_path": health.get("output_schema_path"),
        "assumptions_path": health.get("assumptions_path"),
        "last_batch_run": health.get("last_batch_run"),
        "tests_recorded": health.get("tests_recorded"),
        "dashboard_available": health.get("dashboard_available"),
        "yfinance_live_provider_available": health.get("yfinance_live_provider_available"),
    })
    if health.get("live_market_data") is False:
        st.warning("This dashboard is running on synthetic/no-network construction data. Do not interpret outputs as real market analysis.")
    elif health.get("yfinance_live_provider_available"):
        st.warning("Live yfinance provider endpoint is available, but yfinance_pragmatic remains degraded and may produce UNKNOWN checks for missing fields.")
    st.subheader("Persisted runs (runtime summary)")
    try:
        runtime = client.get_runtime_summary()
    except ApiClientError as exc:
        runtime = None
        st.warning(f"Runtime summary unavailable: {exc}")
    if runtime:
        st.json(runtime)
        if not runtime.get("tickers_available"):
            st.info("No persisted tickers yet. Run: PYTHONPATH=src python -m "
                    "sws_engine.cli real-dashboard-bootstrap --tickers AAPL,MSFT ...")
        st.caption(runtime.get("production_readiness_hint", ""))
    else:
        st.info("Endpoint /meta/runtime-summary not available on this API build.")
    st.subheader("API health")
    st.json({"root": root, "docs": root.get("docs", "/docs"), "health": root.get("health", "/meta/health")})
    render_footer()


if __name__ == "__main__":
    main()
