"""Thin HTTP client for the SWS Snowflake Engine FastAPI backend."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from dashboard.config import DashboardSettings, get_dashboard_settings


class ApiClientError(RuntimeError):
    """Sanitized dashboard-side API error."""


@dataclass
class ApiClient:
    settings: DashboardSettings

    @classmethod
    def from_env(cls) -> "ApiClient":
        return cls(get_dashboard_settings())

    @property
    def base_url(self) -> str:
        return self.settings.api_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.settings.api_key:
            headers["X-API-Key"] = self.settings.api_key
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if "json" in kwargs:
            headers.setdefault("Content-Type", "application/json")
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.settings.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ApiClientError("API unavailable. Check that FastAPI is running and DASHBOARD_API_URL is correct.") from exc
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise ApiClientError(f"API request failed with status {response.status_code}: {detail}")
        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("API returned non-JSON response.") from exc

    def get_root(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/")

    def get_meta_health(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/meta/health")

    def get_runtime_summary(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/meta/runtime-summary")

    def get_companies(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/companies")

    def analyze_company(self, input_payload: Dict[str, Any], persist: bool = True) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/analyze/company", json={"input_payload": input_payload, "persist": persist})

    def analyze_portfolio(self, input_payload: Dict[str, Any], persist: bool = True) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/analyze/portfolio", json={"input_payload": input_payload, "persist": persist})

    def get_company_latest(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/latest")

    def get_company_audit(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/audit")

    def get_company_data_confidence(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/data-confidence")

    def get_company_model_applicability(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/model-applicability")

    def get_company_sensitivity(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/sensitivity")

    def get_company_explain(self, ticker: str, mode: str = "analyst", include_pass: bool = False) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/explain", params={"mode": mode, "include_pass": str(include_pass).lower()})

    def get_company_business_risks(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/business-risks")

    def get_company_workflow(self, ticker: str, include_optional: bool = False) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/companies/{ticker}/workflow", params={"include_optional": str(include_optional).lower()})

    def audit_watchlist(self, watchlist: list[Dict[str, Any]], audit_summaries: Dict[str, Any] | None = None, business_risks: Dict[str, Any] | None = None) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/audit/watchlist", json={"watchlist": watchlist, "audit_summaries": audit_summaries or {}, "business_risks": business_risks or {}})

    def audit_portfolio(self, holdings: list[Dict[str, Any]], audit_summaries: Dict[str, Any] | None = None, business_risks: Dict[str, Any] | None = None, thesis_statuses: Dict[str, Any] | None = None, sensitivity_summaries: Dict[str, Any] | None = None, portfolio_id: str | None = None, valuation_date: str | None = None) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/audit/portfolio", json={
            "holdings": holdings,
            "audit_summaries": audit_summaries or {},
            "business_risks": business_risks or {},
            "thesis_statuses": thesis_statuses or {},
            "sensitivity_summaries": sensitivity_summaries or {},
            "portfolio_id": portfolio_id,
            "valuation_date": valuation_date,
        })

    def generate_memo(self, audit_summary: Dict[str, Any], explanations: Dict[str, Any] | None = None, sensitivity_summary: Dict[str, Any] | None = None, business_risk: Dict[str, Any] | None = None, thesis_status: Dict[str, Any] | None = None, decision_record: Dict[str, Any] | None = None, portfolio_audit: Dict[str, Any] | None = None, mode: str = "analyst") -> Optional[Dict[str, Any]]:
        return self._request("POST", "/research/memo", json={
            "audit_summary": audit_summary,
            "explanations": explanations,
            "sensitivity_summary": sensitivity_summary,
            "business_risk": business_risk,
            "thesis_status": thesis_status,
            "decision_record": decision_record,
            "portfolio_audit": portfolio_audit,
            "mode": mode,
        })

    def compare_runs(self, previous: Dict[str, Any], current: Dict[str, Any], comparison_id: str | None = None, artifact_type: str = "audit_summary") -> Optional[Dict[str, Any]]:
        return self._request("POST", "/research/compare-runs", json={"previous": previous, "current": current, "comparison_id": comparison_id, "artifact_type": artifact_type})

    def build_workflow_package(self, audit_summary: Dict[str, Any], explanations: Dict[str, Any] | None = None, sensitivity_summary: Dict[str, Any] | None = None, business_risk: Dict[str, Any] | None = None, thesis_status: Dict[str, Any] | None = None, decision_record: Dict[str, Any] | None = None, portfolio_audit: Dict[str, Any] | None = None, investment_memo: Dict[str, Any] | None = None, run_comparison: Dict[str, Any] | None = None, workflow_id: str | None = None, mode: str = "analyst") -> Optional[Dict[str, Any]]:
        return self._request("POST", "/research/workflow-package", json={
            "audit_summary": audit_summary,
            "explanations": explanations,
            "sensitivity_summary": sensitivity_summary,
            "business_risk": business_risk,
            "thesis_status": thesis_status,
            "decision_record": decision_record,
            "portfolio_audit": portfolio_audit,
            "investment_memo": investment_memo,
            "run_comparison": run_comparison,
            "workflow_id": workflow_id,
            "mode": mode,
        })

    def get_company_history(self, ticker: str, axis: str | None = None, from_date: str | None = None, to_date: str | None = None) -> Optional[Dict[str, Any]]:
        params = {k: v for k, v in {"axis": axis, "from_date": from_date, "to_date": to_date}.items() if v is not None}
        return self._request("GET", f"/companies/{ticker}/history", params=params)

    def get_company_checks(self, ticker: str, axis: str | None = None, result: str | None = None, reason_code: str | None = None, latest_only: bool = True) -> Optional[Dict[str, Any]]:
        params = {"latest_only": str(latest_only).lower()}
        params.update({k: v for k, v in {"axis": axis, "result": result, "reason_code": reason_code}.items() if v is not None})
        return self._request("GET", f"/companies/{ticker}/checks", params=params)

    def screener(self, axis: str | None = None, min_score: int | None = None, min_coverage: float = 0.66, provider_profile: str | None = None, limit: int = 100) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {"min_coverage": min_coverage, "limit": limit}
        if axis is not None:
            params["axis"] = axis
        if min_score is not None:
            params["min_score"] = min_score
        if provider_profile is not None:
            params["provider_profile"] = provider_profile
        return self._request("GET", "/screener", params=params)

    def get_assumptions_current(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/assumptions/current")

    def get_portfolio_latest(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/portfolios/{portfolio_id}/latest")

    def get_portfolio_history(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/portfolios/{portfolio_id}/history")

    def get_averages_snapshot(self, market: str, date: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/averages/{market}/{date}")
    def build_yfinance_payload(self, ticker: str, valuation_date: str | None = None, market: str | None = None, industry: str | None = None, refresh: bool = False, overrides: Dict[str, Any] | None = None) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/providers/yfinance/build-payload", json={
            "ticker": ticker,
            "valuation_date": valuation_date,
            "market": market,
            "industry": industry,
            "refresh": refresh,
            "overrides": overrides or {},
        })

    def analyze_company_live(self, ticker: str, valuation_date: str | None = None, market: str | None = None, industry: str | None = None, refresh: bool = False, persist: bool = True, overrides: Dict[str, Any] | None = None) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/analyze/company-live", json={
            "ticker": ticker,
            "valuation_date": valuation_date,
            "market": market,
            "industry": industry,
            "refresh": refresh,
            "persist": persist,
            "overrides": overrides or {},
        })

