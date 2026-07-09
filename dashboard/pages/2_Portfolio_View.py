"""Portfolio View page."""
from __future__ import annotations

import json
from typing import Any, Dict

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.footer import render_footer
from dashboard.components.portfolio_components import render_contributors_table, render_portfolio_weighted_scores, render_returns_table
from dashboard.components.warnings_panel import render_warnings
from dashboard.streamlit_compat import st


def _extract_output(response: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not response:
        return None
    return response.get("output", response)


def main() -> None:
    st.set_page_config(page_title="Portfolio View", layout="wide")
    st.title("Portfolio View")
    client = ApiClient.from_env()
    portfolio_id = st.text_input("Portfolio ID", value="portfolio")
    output: Dict[str, Any] | None = None
    if st.button("Load latest portfolio"):
        try:
            output = _extract_output(client.get_portfolio_latest(portfolio_id))
        except ApiClientError as exc:
            st.error(str(exc))
    uploaded = st.file_uploader("Optional: upload portfolio input JSON", type=["json"])
    if uploaded is not None:
        try:
            payload = json.load(uploaded)
            if st.button("Run portfolio analysis via API and persist"):
                output = _extract_output(client.analyze_portfolio(payload, persist=True))
        except Exception as exc:
            st.error(f"Could not process uploaded JSON: {exc.__class__.__name__}")
    if output is None:
        try:
            output = _extract_output(client.get_portfolio_latest(portfolio_id))
        except ApiClientError:
            output = None
    if not output:
        st.info("No portfolio output loaded. Load latest or upload a portfolio payload.")
        render_footer()
        return
    st.header(output.get("portfolio_id") or output.get("name") or portfolio_id)
    st.write({"valuation_date": output.get("valuation_date"), "portfolio_id": output.get("portfolio_id")})
    render_portfolio_weighted_scores(output)
    render_returns_table(output)
    render_contributors_table(output)
    if output.get("fx_split"):
        st.subheader("Price gain vs FX gain")
        st.json(output.get("fx_split"))
    render_warnings(output.get("warnings", []))
    render_footer()


if __name__ == "__main__":
    main()
