"""Audit Workflow Hub page."""
from __future__ import annotations

from typing import Any, Dict

from dashboard.api_client import ApiClient, ApiClientError
from dashboard.components.audit_workflow import render_workflow_package
from dashboard.components.footer import render_footer
from dashboard.streamlit_compat import st


def _unwrap(response: Dict[str, Any] | None, key: str) -> Dict[str, Any] | None:
    if not response:
        return None
    value = response.get(key, response)
    return value if isinstance(value, dict) else None


def _load_optional_company_artifacts(client: ApiClient, ticker: str, include_optional: bool) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    try:
        audit = _unwrap(client.get_company_audit(ticker), "audit")
        if audit:
            artifacts["audit_summary"] = audit
    except ApiClientError as exc:
        st.warning(f"Company audit unavailable: {exc}")
        return artifacts
    if not include_optional:
        return artifacts
    loaders = [
        ("explanations", lambda: _unwrap(client.get_company_explain(ticker), "explanations")),
        ("sensitivity_summary", lambda: _unwrap(client.get_company_sensitivity(ticker), "sensitivity")),
        ("business_risk", lambda: _unwrap(client.get_company_business_risks(ticker), "business_risks")),
    ]
    for key, loader in loaders:
        try:
            value = loader()
            if value:
                artifacts[key] = value
        except ApiClientError as exc:
            st.info(f"Optional component `{key}` unavailable: {exc}")
    return artifacts


def main() -> None:
    st.set_page_config(page_title="Audit Workflow Hub", layout="wide")
    st.title("Audit Workflow Hub")
    st.caption("API-only decision-hygiene surface. It summarizes workflow state; it does not issue investment recommendations.")
    client = ApiClient.from_env()
    ticker = st.text_input("Ticker", value="DEMO")
    include_optional = st.checkbox("Attempt optional API components", value=False)
    package = None
    if st.button("Build workflow package"):
        artifacts = _load_optional_company_artifacts(client, ticker, include_optional)
        audit = artifacts.get("audit_summary")
        if not audit:
            st.warning("No audit summary was loaded; workflow package cannot be complete.")
        else:
            try:
                response = client.build_workflow_package(
                    audit_summary=audit,
                    explanations=artifacts.get("explanations"),
                    sensitivity_summary=artifacts.get("sensitivity_summary"),
                    business_risk=artifacts.get("business_risk"),
                    workflow_id=f"{ticker.upper()}-dashboard-workflow",
                )
                package = _unwrap(response, "workflow_package")
            except ApiClientError as exc:
                st.error(str(exc))
    if package is not None:
        render_workflow_package(package)
    else:
        st.info("Load a persisted ticker first. The page calls FastAPI endpoints through dashboard.api_client only.")
    render_footer()


if __name__ == "__main__":
    main()
