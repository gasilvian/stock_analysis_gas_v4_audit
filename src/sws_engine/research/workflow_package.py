"""P0.13 Research workflow package foundation.

This module produces a compact, deterministic API/dashboard-ready package from
existing v4.0 audit artifacts. It is intentionally additive: it does not rerun
checks, does not fetch live data, does not mutate canonical v3.1 output, and does
not interpret any artifact as an investment recommendation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

FORBIDDEN_RECOMMENDATION_TOKENS = [
    " BUY ",
    " SELL ",
    " HOLD ",
    "BUY/SELL/HOLD",
    "Buy rating",
    "Sell rating",
    "Hold rating",
    "price target",
    "target price",
    "recommendation to",
    "overweight recommendation",
    "underweight recommendation",
    "rebalance into",
]

COMPONENTS = [
    {
        "id": "audit_summary",
        "label": "Company Audit",
        "required": True,
        "artifact_key": "audit_summary",
        "api_method": "GET",
        "api_path_template": "/companies/{ticker}/audit",
        "dashboard_surface": "Company View / Audit Workflow Hub",
    },
    {
        "id": "explanations",
        "label": "Reason-code explanations",
        "required": False,
        "artifact_key": "explanations",
        "api_method": "GET",
        "api_path_template": "/companies/{ticker}/explain",
        "dashboard_surface": "Audit Workflow Hub",
    },
    {
        "id": "sensitivity_summary",
        "label": "Sensitivity and valuation range",
        "required": False,
        "artifact_key": "sensitivity_summary",
        "api_method": "GET",
        "api_path_template": "/companies/{ticker}/sensitivity",
        "dashboard_surface": "Audit Workflow Hub",
    },
    {
        "id": "business_risk",
        "label": "Business risk signals",
        "required": False,
        "artifact_key": "business_risk",
        "api_method": "GET",
        "api_path_template": "/companies/{ticker}/business-risks",
        "dashboard_surface": "Audit Workflow Hub",
    },
    {
        "id": "thesis_status",
        "label": "Thesis status",
        "required": False,
        "artifact_key": "thesis_status",
        "api_method": "POST",
        "api_path_template": "/research/thesis/evaluate",
        "dashboard_surface": "Audit Workflow Hub",
    },
    {
        "id": "decision_record",
        "label": "Decision journal context",
        "required": False,
        "artifact_key": "decision_record",
        "api_method": "POST",
        "api_path_template": "/research/decision",
        "dashboard_surface": "Audit Workflow Hub",
    },
    {
        "id": "portfolio_audit",
        "label": "Portfolio audit context",
        "required": False,
        "artifact_key": "portfolio_audit",
        "api_method": "POST",
        "api_path_template": "/audit/portfolio",
        "dashboard_surface": "Portfolio View / Audit Workflow Hub",
    },
    {
        "id": "investment_memo",
        "label": "Investment audit memo",
        "required": False,
        "artifact_key": "investment_memo",
        "api_method": "POST",
        "api_path_template": "/research/memo",
        "dashboard_surface": "Audit Workflow Hub",
    },
    {
        "id": "run_comparison",
        "label": "Run comparison",
        "required": False,
        "artifact_key": "run_comparison",
        "api_method": "POST",
        "api_path_template": "/research/compare-runs",
        "dashboard_surface": "Audit Workflow Hub",
    },
]

WORKFLOW_STEPS = [
    "audit_summary",
    "explanations",
    "sensitivity_summary",
    "business_risk",
    "thesis_status",
    "decision_record",
    "portfolio_audit",
    "investment_memo",
    "run_comparison",
]


def load_json_artifact(path: str | Path | None, *, required: bool = False) -> dict[str, Any] | None:
    if not path:
        if required:
            raise FileNotFoundError("Required workflow artifact path was not provided")
        return None
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(f"Workflow artifact not found: {p}")
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Workflow artifact must be a JSON object: {p}")
    return data


def build_workflow_package(
    *,
    audit_summary: Mapping[str, Any] | None,
    explanations: Mapping[str, Any] | None = None,
    sensitivity_summary: Mapping[str, Any] | None = None,
    business_risk: Mapping[str, Any] | None = None,
    thesis_status: Mapping[str, Any] | None = None,
    decision_record: Mapping[str, Any] | None = None,
    portfolio_audit: Mapping[str, Any] | None = None,
    investment_memo: Mapping[str, Any] | None = None,
    run_comparison: Mapping[str, Any] | None = None,
    workflow_id: str | None = None,
    mode: str = "analyst",
) -> dict[str, Any]:
    """Build an API/dashboard-ready workflow-state package from local artifacts."""
    artifacts: dict[str, Mapping[str, Any] | None] = {
        "audit_summary": audit_summary,
        "explanations": explanations,
        "sensitivity_summary": sensitivity_summary,
        "business_risk": business_risk,
        "thesis_status": thesis_status,
        "decision_record": decision_record,
        "portfolio_audit": portfolio_audit,
        "investment_memo": investment_memo,
        "run_comparison": run_comparison,
    }
    if not audit_summary:
        return _unknown_package(workflow_id=workflow_id, mode=mode, artifacts=artifacts)

    audit = dict(audit_summary)
    ticker = _first_non_empty(
        audit.get("ticker"),
        _nested(sensitivity_summary, "ticker"),
        _nested(business_risk, "ticker"),
        _nested(thesis_status, "ticker"),
        _nested(investment_memo, "ticker"),
        "UNKNOWN",
    ).upper()
    run_id = _first_non_empty(audit.get("run_id"), _nested(investment_memo, "run_id"), "UNKNOWN")

    component_status = [_component_status(defn, ticker, artifacts.get(defn["artifact_key"])) for defn in COMPONENTS]
    workflow_steps = [_workflow_step(defn, status) for defn, status in zip(COMPONENTS, component_status)]
    unknown_summary = _unknown_summary(artifacts)
    readiness_summary = _readiness_summary(component_status, unknown_summary)
    manual_review_items = _manual_review_items(component_status, unknown_summary, artifacts)
    status = "PASS" if not manual_review_items and readiness_summary["missing_required_count"] == 0 else "PASS_WITH_LIMITATIONS"
    reason_code = "WORKFLOW_PACKAGE_READY"
    if readiness_summary["missing_required_count"]:
        status = "UNKNOWN"
        reason_code = "WORKFLOW_PACKAGE_INPUTS_MISSING"
    elif unknown_summary["total_unknown_indicators"]:
        reason_code = "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED"
    elif manual_review_items:
        reason_code = "WORKFLOW_PACKAGE_MANUAL_REVIEW_REQUIRED"

    package = {
        "schema_version": "workflow_package.v0.1",
        "sprint": "v4.0-p0.13",
        "status": status,
        "reason_code": reason_code,
        "workflow_id": workflow_id or f"{ticker.lower()}-workflow",
        "ticker": ticker,
        "run_id": run_id,
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "component_status": component_status,
        "workflow_steps": workflow_steps,
        "readiness_summary": readiness_summary,
        "unknown_summary": unknown_summary,
        "manual_review_items": manual_review_items,
        "api_wiring": _api_wiring(ticker),
        "dashboard_surfaces": _dashboard_surfaces(),
        "input_lineage": _input_lineage(artifacts),
        "recommendation_language_absent": True,
        "recommendation_guardrail": {"recommendation_language_absent": True, "forbidden_tokens_detected": []},
        "limitations": [
            "P0.13 packages existing local/API artifacts for dashboard workflow visibility; it does not rerun the engine.",
            "Missing artifacts remain visible as missing or UNKNOWN components; no substitute values are invented.",
            "This package is a research-process state summary, not an investment recommendation.",
            "Dashboard surfaces must access data through the API client rather than backend internals.",
        ],
        "not_investment_advice": True,
    }
    return package


def workflow_package_from_files(
    *,
    audit_summary_path: str | Path,
    explanations_path: str | Path | None = None,
    sensitivity_path: str | Path | None = None,
    business_risk_path: str | Path | None = None,
    thesis_status_path: str | Path | None = None,
    decision_record_path: str | Path | None = None,
    portfolio_audit_path: str | Path | None = None,
    investment_memo_path: str | Path | None = None,
    run_comparison_path: str | Path | None = None,
    workflow_id: str | None = None,
    mode: str = "analyst",
) -> dict[str, Any]:
    return build_workflow_package(
        audit_summary=load_json_artifact(audit_summary_path, required=True),
        explanations=load_json_artifact(explanations_path),
        sensitivity_summary=load_json_artifact(sensitivity_path),
        business_risk=load_json_artifact(business_risk_path),
        thesis_status=load_json_artifact(thesis_status_path),
        decision_record=load_json_artifact(decision_record_path),
        portfolio_audit=load_json_artifact(portfolio_audit_path),
        investment_memo=load_json_artifact(investment_memo_path),
        run_comparison=load_json_artifact(run_comparison_path),
        workflow_id=workflow_id,
        mode=mode,
    )


def workflow_package_to_files(
    output_dir: str | Path,
    *,
    audit_summary_path: str | Path,
    explanations_path: str | Path | None = None,
    sensitivity_path: str | Path | None = None,
    business_risk_path: str | Path | None = None,
    thesis_status_path: str | Path | None = None,
    decision_record_path: str | Path | None = None,
    portfolio_audit_path: str | Path | None = None,
    investment_memo_path: str | Path | None = None,
    run_comparison_path: str | Path | None = None,
    workflow_id: str | None = None,
    mode: str = "analyst",
) -> dict[str, Any]:
    package = workflow_package_from_files(
        audit_summary_path=audit_summary_path,
        explanations_path=explanations_path,
        sensitivity_path=sensitivity_path,
        business_risk_path=business_risk_path,
        thesis_status_path=thesis_status_path,
        decision_record_path=decision_record_path,
        portfolio_audit_path=portfolio_audit_path,
        investment_memo_path=investment_memo_path,
        run_comparison_path=run_comparison_path,
        workflow_id=workflow_id,
        mode=mode,
    )
    return {"package": package, "paths": write_workflow_package_artifacts(package, output_dir)}


def render_workflow_package_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        "# Research Workflow Package",
        "",
        "## Verdict",
        "",
        f"- Status: `{package.get('status')}`",
        f"- Reason code: `{package.get('reason_code')}`",
        f"- Ticker: `{package.get('ticker')}`",
        f"- Run ID: `{package.get('run_id')}`",
        f"- Workflow ID: `{package.get('workflow_id')}`",
        "",
        "## Workflow readiness",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    readiness = package.get("readiness_summary") or {}
    for key in [
        "ready_count",
        "missing_required_count",
        "missing_optional_count",
        "unknown_component_count",
        "manual_review_count",
        "ready_for_deep_dive",
        "ready_for_memo",
    ]:
        lines.append(f"| `{key}` | `{readiness.get(key, 'UNKNOWN')}` |")

    lines += ["", "## Components", "", "| Component | Status | Required | Reason code | API path |", "|---|---|---:|---|---|"]
    for row in package.get("component_status") or []:
        lines.append(
            f"| {row.get('label')} | `{row.get('status')}` | `{row.get('required')}` | `{row.get('reason_code')}` | `{row.get('api_path')}` |"
        )

    lines += ["", "## What remains UNKNOWN", ""]
    unknown = package.get("unknown_summary") or {}
    lines.append(f"- Total UNKNOWN indicators: `{unknown.get('total_unknown_indicators')}`")
    lines.append(f"- Components with UNKNOWN: `{', '.join(unknown.get('components_with_unknown') or []) or 'none'}`")
    lines.append(f"- Critical missing inputs count: `{unknown.get('critical_missing_inputs_count')}`")
    for field in unknown.get("critical_missing_inputs") or []:
        lines.append(f"  - `{field}`")

    lines += ["", "## Manual review items", ""]
    items = package.get("manual_review_items") or []
    if items:
        for item in items:
            lines.append(f"- {item}")
    else:
        lines.append("- None from workflow packaging rules.")

    lines += ["", "## API wiring", "", "| Surface | Method | Path |", "|---|---|---|"]
    for key, value in (package.get("api_wiring") or {}).items():
        lines.append(f"| `{key}` | `{value.get('method')}` | `{value.get('path')}` |")

    lines += ["", "## Limitations", ""]
    for item in package.get("limitations") or []:
        lines.append(f"- {item}")
    text = "\n".join(lines) + FOOTER
    _ensure_no_recommendation_language(text)
    return text


def write_workflow_package_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(package.get("ticker") or "UNKNOWN").upper()
    json_path = out / f"{ticker}_workflow_package.json"
    md_path = out / f"{ticker}_workflow_package_report.md"
    json_text = json.dumps(package, indent=2, sort_keys=True)
    _ensure_no_recommendation_language(f" {json_text} ")
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(render_workflow_package_report_md(package), encoding="utf-8")
    return {"workflow_package_json": str(json_path), "workflow_package_report": str(md_path)}


def _unknown_package(*, workflow_id: str | None, mode: str, artifacts: Mapping[str, Mapping[str, Any] | None]) -> dict[str, Any]:
    component_status = [_component_status(defn, "UNKNOWN", artifacts.get(defn["artifact_key"])) for defn in COMPONENTS]
    return {
        "schema_version": "workflow_package.v0.1",
        "sprint": "v4.0-p0.13",
        "status": "UNKNOWN",
        "reason_code": "WORKFLOW_PACKAGE_INPUTS_MISSING",
        "workflow_id": workflow_id or "unknown-workflow",
        "ticker": "UNKNOWN",
        "run_id": "UNKNOWN",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "component_status": component_status,
        "workflow_steps": [_workflow_step(defn, status) for defn, status in zip(COMPONENTS, component_status)],
        "readiness_summary": {
            "ready_count": 0,
            "missing_required_count": 1,
            "missing_optional_count": 0,
            "unknown_component_count": 1,
            "manual_review_count": 1,
            "ready_for_deep_dive": False,
            "ready_for_memo": False,
        },
        "unknown_summary": {"total_unknown_indicators": 1, "components_with_unknown": ["audit_summary"], "critical_missing_inputs": [], "critical_missing_inputs_count": 0},
        "manual_review_items": ["Required audit_summary artifact is missing; workflow state cannot be trusted."],
        "api_wiring": _api_wiring("UNKNOWN"),
        "dashboard_surfaces": _dashboard_surfaces(),
        "input_lineage": [],
        "recommendation_language_absent": True,
        "recommendation_guardrail": {"recommendation_language_absent": True, "forbidden_tokens_detected": []},
        "limitations": ["Required workflow input is missing."],
        "not_investment_advice": True,
    }


def _component_status(defn: Mapping[str, Any], ticker: str, artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    required = bool(defn.get("required"))
    if artifact is None:
        status = "MISSING_REQUIRED" if required else "MISSING_OPTIONAL"
        reason_code = "WORKFLOW_PACKAGE_INPUTS_MISSING" if required else "WORKFLOW_OPTIONAL_COMPONENT_MISSING"
        unknown_count = 1 if required else 0
    else:
        unknown_count = _artifact_unknown_count(artifact)
        status = "UNKNOWN_PRESENT" if unknown_count else "READY"
        reason_code = "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED" if unknown_count else "WORKFLOW_COMPONENT_READY"
    return {
        "component_id": defn["id"],
        "label": defn["label"],
        "required": required,
        "status": status,
        "reason_code": reason_code,
        "unknown_indicators_count": unknown_count,
        "api_method": defn["api_method"],
        "api_path": defn["api_path_template"].format(ticker=ticker),
        "dashboard_surface": defn["dashboard_surface"],
        "manual_review_required": status in {"MISSING_REQUIRED", "UNKNOWN_PRESENT"},
    }


def _workflow_step(defn: Mapping[str, Any], status: Mapping[str, Any]) -> dict[str, Any]:
    if status["status"] == "READY":
        step_status = "READY"
    elif status["status"] == "MISSING_OPTIONAL":
        step_status = "OPTIONAL_MISSING"
    elif status["status"] == "UNKNOWN_PRESENT":
        step_status = "MANUAL_REVIEW"
    else:
        step_status = "BLOCKED"
    return {
        "step_id": defn["id"],
        "label": defn["label"],
        "status": step_status,
        "reason_code": status["reason_code"],
        "api_method": status["api_method"],
        "api_path": status["api_path"],
        "dashboard_surface": status["dashboard_surface"],
    }


def _readiness_summary(component_status: list[Mapping[str, Any]], unknown_summary: Mapping[str, Any]) -> dict[str, Any]:
    ready = sum(1 for c in component_status if c["status"] == "READY")
    missing_required = sum(1 for c in component_status if c["status"] == "MISSING_REQUIRED")
    missing_optional = sum(1 for c in component_status if c["status"] == "MISSING_OPTIONAL")
    unknown_components = sum(1 for c in component_status if c["status"] == "UNKNOWN_PRESENT")
    manual_review = sum(1 for c in component_status if c.get("manual_review_required"))
    present = {c["component_id"]: c["status"] for c in component_status}
    ready_for_deep_dive = present.get("audit_summary") in {"READY", "UNKNOWN_PRESENT"} and present.get("sensitivity_summary") != "MISSING_OPTIONAL"
    ready_for_memo = present.get("audit_summary") in {"READY", "UNKNOWN_PRESENT"} and present.get("investment_memo") != "MISSING_OPTIONAL"
    return {
        "ready_count": ready,
        "missing_required_count": missing_required,
        "missing_optional_count": missing_optional,
        "unknown_component_count": unknown_components,
        "manual_review_count": manual_review,
        "total_unknown_indicators": int(unknown_summary.get("total_unknown_indicators") or 0),
        "ready_for_deep_dive": bool(ready_for_deep_dive),
        "ready_for_memo": bool(ready_for_memo),
    }


def _unknown_summary(artifacts: Mapping[str, Mapping[str, Any] | None]) -> dict[str, Any]:
    components: list[str] = []
    critical_missing: list[str] = []
    total = 0
    for key, artifact in artifacts.items():
        if not artifact:
            continue
        count = _artifact_unknown_count(artifact)
        if count:
            total += count
            components.append(key)
        critical_missing.extend(_critical_missing_inputs(artifact))
    critical_unique = sorted(set(critical_missing))
    return {
        "total_unknown_indicators": total,
        "components_with_unknown": sorted(set(components)),
        "critical_missing_inputs": critical_unique,
        "critical_missing_inputs_count": len(critical_unique),
    }


def _manual_review_items(component_status: list[Mapping[str, Any]], unknown_summary: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any] | None]) -> list[str]:
    items: list[str] = []
    for row in component_status:
        if row["status"] == "MISSING_REQUIRED":
            items.append(f"Required component `{row['component_id']}` is missing; workflow package cannot be complete.")
        elif row["status"] == "UNKNOWN_PRESENT":
            items.append(f"Component `{row['component_id']}` contains UNKNOWN indicators; review before relying on downstream memo/reporting.")
    if unknown_summary.get("critical_missing_inputs_count"):
        items.append(f"Critical missing inputs remain visible: {', '.join(unknown_summary.get('critical_missing_inputs') or [])}.")
    audit = artifacts.get("audit_summary") or {}
    if audit.get("provider_degradation_visible"):
        items.append("Provider degradation is visible in audit_summary and must remain visible in dashboard interpretation.")
    return sorted(set(items))


def _api_wiring(ticker: str) -> dict[str, dict[str, str]]:
    return {
        defn["id"]: {
            "method": str(defn["api_method"]),
            "path": str(defn["api_path_template"]).format(ticker=ticker),
        }
        for defn in COMPONENTS
    }


def _dashboard_surfaces() -> list[dict[str, str]]:
    return [
        {"surface": "Company View", "path": "dashboard/pages/1_Company_View.py", "api_only": "true"},
        {"surface": "Portfolio View", "path": "dashboard/pages/2_Portfolio_View.py", "api_only": "true"},
        {"surface": "Audit Workflow Hub", "path": "dashboard/pages/6_Audit_Workflow_Hub.py", "api_only": "true"},
    ]


def _input_lineage(artifacts: Mapping[str, Mapping[str, Any] | None]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, artifact in artifacts.items():
        if not artifact:
            continue
        rows.append({
            "component_id": key,
            "schema_version": artifact.get("schema_version", "UNKNOWN"),
            "reason_code": artifact.get("reason_code", "UNKNOWN"),
            "status": artifact.get("status", "UNKNOWN"),
            "source_class": artifact.get("source_class", artifact.get("source_tier", "auxiliary_artifact")),
            "source_quality": artifact.get("source_quality", "artifact"),
        })
    return rows


def _artifact_unknown_count(artifact: Mapping[str, Any]) -> int:
    count = 0
    text = json.dumps(artifact, sort_keys=True, default=str)
    count += text.count("UNKNOWN")
    if artifact.get("status") == "UNKNOWN":
        count += 1
    if artifact.get("reason_code") in {"MEMO_COMPONENT_UNKNOWN", "RUN_COMPARISON_UNKNOWN_PRESERVED", "WORKFLOW_PACKAGE_UNKNOWN_PRESERVED"}:
        count += 1
    if artifact.get("unknown_summary"):
        us = artifact.get("unknown_summary") or {}
        count += int(us.get("total_unknown_indicators") or 0) if str(us.get("total_unknown_indicators") or "").isdigit() else 0
    return count


def _critical_missing_inputs(artifact: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("critical_missing_inputs", "critical_missing_inputs_current"):
        raw = artifact.get(key)
        if isinstance(raw, list):
            values.extend(_stringify_missing(raw))
    data_conf = artifact.get("data_confidence") or {}
    if isinstance(data_conf, Mapping):
        raw = data_conf.get("critical_missing_inputs")
        if isinstance(raw, list):
            values.extend(_stringify_missing(raw))
    unknown_summary = artifact.get("unknown_summary") or {}
    if isinstance(unknown_summary, Mapping):
        raw = unknown_summary.get("critical_missing_inputs")
        if isinstance(raw, list):
            values.extend(_stringify_missing(raw))
    unknown_changes = artifact.get("unknown_changes") or {}
    if isinstance(unknown_changes, Mapping):
        raw = unknown_changes.get("critical_missing_inputs_current") or []
        if isinstance(raw, list):
            values.extend(_stringify_missing(raw))
    return values


def _stringify_missing(values: list[Any]) -> list[str]:
    out: list[str] = []
    for item in values:
        if isinstance(item, Mapping):
            out.append(str(item.get("field") or item.get("input") or item.get("name") or item))
        else:
            out.append(str(item))
    return [x for x in out if x]


def _ensure_no_recommendation_language(text: str) -> None:
    for token in FORBIDDEN_RECOMMENDATION_TOKENS:
        if token in text:
            raise ValueError(f"Forbidden recommendation language detected: {token.strip()}")


def _nested(obj: Mapping[str, Any] | None, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return None


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return "UNKNOWN"
