"""Company View page."""
from __future__ import annotations

import json
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.badges import render_provider_badge
from dashboard.components.checks_table import render_checks_table
from dashboard.components.footer import render_footer
from dashboard.components.lineage_panel import render_lineage_panel
from dashboard.components.score_cards import render_score_cards
from dashboard.components.snowflake_radar import render_snowflake_radar
from dashboard.components.valuation_card import render_valuation_card
from dashboard.components.warnings_panel import render_warnings
from dashboard.streamlit_compat import st

AXES = ["value", "future", "past", "health", "dividend"]


def _extract_output(response: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not response:
        return None
    return response.get("output", response)


def _render_banners(output: Dict[str, Any]) -> None:
    provider = output.get("provider_profile")
    warnings = output.get("warnings", []) or []
    if provider == "yfinance_pragmatic":
        st.warning("Provider degradation: yfinance_pragmatic is a pragmatic approximation, not a faithful SWS replication.")
    joined = "\n".join(str(w) for w in warnings)
    if "DEMO_FIXTURE_ONLY" in joined or "SYNTHETIC_CURATED_DATA" in joined:
        st.warning("Synthetic/demo data is present. Do not interpret this as real market analysis.")


def _render_header(output: Dict[str, Any]) -> None:
    st.header(f"{output.get('ticker', 'UNKNOWN')} ({output.get('exchange', 'UNKNOWN')})")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Valuation date", output.get("valuation_date", "UNKNOWN"))
    with cols[1]:
        render_provider_badge(output.get("provider_profile"))
    with cols[2]:
        st.metric("Model", output.get("valuation_model", "UNKNOWN"))
    with cols[3]:
        st.metric("Variant", output.get("valuation_variant", "UNKNOWN"))


def _render_audit_panel(client: ApiClient, ticker: str) -> None:
    st.subheader("Company Audit — P0.1")
    try:
        response = client.get_company_audit(ticker)
    except ApiClientError as exc:
        st.warning(f"Audit endpoint unavailable: {exc}")
        return
    if not response:
        st.info("No audit summary available for this ticker.")
        return
    audit = response.get("audit", response)
    data_conf = audit.get("data_confidence", {})
    model_app = audit.get("model_applicability", {})
    risk = audit.get("conclusion_risk", {})
    cols = st.columns(3)
    with cols[0]:
        st.metric("Data confidence", data_conf.get("level", "UNKNOWN"))
        st.caption(f"grade: {data_conf.get('confidence_grade', 'UNKNOWN')}")
    with cols[1]:
        st.metric("Model applicability", model_app.get("status", "UNKNOWN"))
        st.caption(model_app.get("reason_code", "UNKNOWN"))
    with cols[2]:
        st.metric("Conclusion risk", risk.get("risk_level", "UNKNOWN"))
        st.caption(f"allowed usage: {model_app.get('allowed_score_usage', 'UNKNOWN')}")
    if audit.get("provider_degradation_visible"):
        st.warning("Provider degradation is visible in the audit layer. Treat pragmatic source fields as limited until reviewed.")

    tier_mix = data_conf.get("source_tier_mix") or {}
    if tier_mix:
        st.caption("Source tier mix from available field lineage")
        st.dataframe(pd.DataFrame([{"source_tier": k, "count": v} for k, v in tier_mix.items()]), use_container_width=True)

    stale_fields = data_conf.get("stale_fields") or []
    if stale_fields:
        st.warning(f"Stale fields detected: {len(stale_fields)}")
        st.dataframe(pd.DataFrame(stale_fields), use_container_width=True)

    if model_app.get("identifier_master_used"):
        st.info("Model applicability used Identifier Master metadata.")

    missing = audit.get("critical_missing_inputs", [])
    if missing:
        st.warning(f"Critical missing inputs detected: {len(missing)}")
        st.dataframe(pd.DataFrame(missing), use_container_width=True)
    clusters = audit.get("unknown_clusters", [])
    if clusters:
        st.warning(f"UNKNOWN clusters detected: {len(clusters)}")
        st.dataframe(pd.DataFrame([{
            "reason_code": c.get("reason_code"),
            "count": c.get("count"),
        } for c in clusters]), use_container_width=True)
    with st.expander("Audit JSON"):
        st.json(audit)


def _render_history(client: ApiClient, ticker: str) -> None:
    st.subheader("History")
    axis = st.selectbox("History axis", AXES, index=3)
    try:
        history = client.get_company_history(ticker, axis=axis)
    except ApiClientError as exc:
        st.warning(str(exc))
        return
    if not history:
        st.info("No persisted history found. Run analysis with persist=true or run batch first.")
        return
    points = history.get("points", [])
    if not points:
        st.info("No history points returned.")
        return
    df = pd.DataFrame(points)
    if "coverage_pct" not in df.columns:
        st.error("History response is missing coverage_pct; dashboard will not display score-only history.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["valuation_date"], y=df["score_raw"], mode="lines+markers", name="score_raw"))
    fig.update_layout(yaxis={"range": [0, 6]}, xaxis_title="valuation_date", yaxis_title="score_raw")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df[["valuation_date", "score_raw", "known_checks_count", "unknown_checks_count", "coverage_pct", "provider_profile", "run_id"]], use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Company View", layout="wide")
    st.title("Company View")
    client = ApiClient.from_env()

    data_source = st.radio(
        "Data source",
        ["Existing persisted/latest", "Upload JSON", "yfinance live"],
        horizontal=True,
    )
    try:
        persisted = (client.get_companies() or {}).get("tickers", [])
    except ApiClientError:
        persisted = []
    default_ticker = "DEMO"
    if persisted:
        options = ["(type manually)"] + [c["ticker"] for c in persisted]
        picked = st.selectbox("Persisted tickers (from DB)", options)
        if picked != "(type manually)":
            default_ticker = picked
    ticker = st.text_input("Ticker", value=default_ticker)
    output: Dict[str, Any] | None = None
    if data_source == "Existing persisted/latest" and st.button("Load latest"):
        try:
            output = _extract_output(client.get_company_latest(ticker))
        except ApiClientError as exc:
            st.error(str(exc))

    if data_source == "Upload JSON":
        uploaded = st.file_uploader("Optional: upload company input JSON", type=["json"])
        if uploaded is not None:
            try:
                payload = json.load(uploaded)
                if st.button("Run analysis via API and persist"):
                    output = _extract_output(client.analyze_company(payload, persist=True))
            except Exception as exc:  # Streamlit UI should sanitize display.
                st.error(f"Could not process uploaded JSON: {exc.__class__.__name__}")

    if data_source == "yfinance live":
        st.warning("LIVE YFINANCE PRAGMATIC: provider coverage may be incomplete; UNKNOWN results reflect missing inputs.")
        market = st.text_input("Market", value="US")
        industry = st.text_input("Industry", value="Technology")
        refresh = st.checkbox("Refresh live provider cache", value=False)
        if st.button("Run live analysis"):
            try:
                output = _extract_output(client.analyze_company_live(
                    ticker=ticker, market=market, industry=industry, refresh=refresh, persist=True))
            except ApiClientError as exc:
                st.error(f"Live provider unavailable or failed: {exc}")

    if output is None:
        try:
            output = _extract_output(client.get_company_latest(ticker))
        except ApiClientError:
            output = None
    if not output:
        st.info("No company output loaded. Load latest for a persisted ticker or upload a payload and run analysis.")
        render_footer()
        return

    _render_header(output)
    _render_banners(output)
    _render_audit_panel(client, output.get("ticker", ticker))
    render_score_cards(output.get("scores", {}))
    left, right = st.columns([1, 1])
    with left:
        render_snowflake_radar(output.get("scores", {}))
    with right:
        render_valuation_card(output)
    render_checks_table(output.get("checks", []))
    render_warnings(output.get("warnings", []))
    render_lineage_panel(output.get("lineage", {}))
    _render_history(client, output.get("ticker", ticker))
    render_footer()


if __name__ == "__main__":
    main()
