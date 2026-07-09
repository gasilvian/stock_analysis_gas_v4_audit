"""P0.11 Investment Memo Generator foundation.

This module composes a deterministic research-audit memo from already-produced
company audit artifacts. It never fetches live data, never produces
recommendation language, never modifies the canonical v3.1 output schema, and
keeps UNKNOWN / limitations visible instead of filling gaps.
"""
from __future__ import annotations

import json
import re
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


def load_json_artifact(path: str | Path | None, *, required: bool = False) -> dict[str, Any] | None:
    if not path:
        if required:
            raise FileNotFoundError("Required artifact path was not provided")
        return None
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(f"Artifact not found: {p}")
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Artifact must be a JSON object: {p}")
    return data


def build_investment_memo_package(
    *,
    audit_summary: Mapping[str, Any] | None,
    explanations: Mapping[str, Any] | None = None,
    sensitivity_summary: Mapping[str, Any] | None = None,
    business_risk: Mapping[str, Any] | None = None,
    thesis_status: Mapping[str, Any] | None = None,
    decision_record: Mapping[str, Any] | None = None,
    portfolio_audit: Mapping[str, Any] | None = None,
    memo_type: str = "investment_audit",
    mode: str = "analyst",
) -> dict[str, Any]:
    """Build a deterministic company research memo package.

    The memo is an audit artifact, not a model output and not advice. The audit
    summary is the only required artifact because it anchors ticker, lineage and
    UNKNOWN policy. Optional artifacts enrich the memo but missing ones remain
    visible as component UNKNOWN entries.
    """
    audit = dict(audit_summary or {})
    if not audit:
        return _unknown_memo(memo_type=memo_type, mode=mode)

    ticker = str(audit.get("ticker") or "UNKNOWN").upper()
    component_status = _component_status(
        audit,
        explanations=explanations,
        sensitivity_summary=sensitivity_summary,
        business_risk=business_risk,
        thesis_status=thesis_status,
        decision_record=decision_record,
        portfolio_audit=portfolio_audit,
    )
    unknown_summary = _unknown_summary(audit, component_status)
    manual_review_items = _manual_review_items(
        audit,
        component_status,
        sensitivity_summary=sensitivity_summary,
        business_risk=business_risk,
        thesis_status=thesis_status,
        portfolio_audit=portfolio_audit,
    )
    sections = {
        "executive_audit_view": _executive_audit_view(audit, component_status, unknown_summary),
        "score_and_coverage": _score_and_coverage_section(audit),
        "data_confidence": _data_confidence_section(audit),
        "model_applicability": _model_applicability_section(audit),
        "conclusion_risk": _conclusion_risk_section(audit),
        "sensitivity_and_valuation_range": _sensitivity_section(sensitivity_summary),
        "business_risk": _business_risk_section(business_risk),
        "thesis_status": _thesis_section(thesis_status),
        "decision_context": _decision_section(decision_record),
        "portfolio_context": _portfolio_context_section(portfolio_audit, ticker),
        "unknown_and_limitations": _unknown_limitations_section(audit, unknown_summary, component_status),
    }
    recommendation_guardrail = _recommendation_guardrail(sections)
    status = "PASS_WITH_LIMITATIONS"
    reason_code = "MEMO_GENERATED"
    if unknown_summary["unknown_checks_count"] or component_status["missing_components"] or manual_review_items:
        reason_code = "MEMO_MANUAL_REVIEW_REQUIRED"
    package = {
        "schema_version": "investment_memo.v0.1",
        "sprint": "v4.0-p0.11",
        "status": status,
        "reason_code": reason_code,
        "ticker": ticker,
        "exchange": audit.get("exchange") or "UNKNOWN",
        "valuation_date": audit.get("valuation_date") or "UNKNOWN",
        "memo_type": memo_type,
        "mode": mode,
        "run_id": audit.get("run_id"),
        "input_snapshot_id": audit.get("input_snapshot_id"),
        "assumptions_hash": audit.get("assumptions_hash"),
        "provider_profile": audit.get("provider_profile") or "UNKNOWN",
        "component_status": component_status,
        "sections": sections,
        "unknown_summary": unknown_summary,
        "manual_review_items": manual_review_items,
        "recommendation_language_absent": recommendation_guardrail["recommendation_language_absent"],
        "recommendation_guardrail": recommendation_guardrail,
        "false_precision_guardrail": _false_precision_guardrail(sensitivity_summary),
        "source_quality": _aggregate_source_quality(audit, explanations, sensitivity_summary, business_risk, thesis_status, decision_record, portfolio_audit),
        "source_class": _aggregate_source_class(audit, explanations, sensitivity_summary, business_risk, thesis_status, decision_record, portfolio_audit),
        "input_lineage": {
            "audit_summary": _artifact_lineage(audit),
            "explanations_present": bool(explanations),
            "sensitivity_summary_present": bool(sensitivity_summary),
            "business_risk_present": bool(business_risk),
            "thesis_status_present": bool(thesis_status),
            "decision_record_present": bool(decision_record),
            "portfolio_audit_present": bool(portfolio_audit),
        },
        "limitations": [
            "P0.11 generates a deterministic research-audit memo from existing artifacts; it does not fetch live data.",
            "The memo is not a recommendation and does not contain recommendation-language by design.",
            "Missing optional artifacts remain UNKNOWN and are listed in component_status and manual review items.",
            "Fair value is displayed only through valuation ranges when sensitivity artifacts exist; point-only conclusions are not promoted.",
        ],
        "not_investment_advice": True,
    }
    if not package["recommendation_language_absent"]:
        package["status"] = "FAIL"
        package["reason_code"] = "MEMO_RECOMMENDATION_LANGUAGE_REJECTED"
    return package


def investment_memo_from_files(
    *,
    audit_summary_path: str | Path,
    explanations_path: str | Path | None = None,
    sensitivity_path: str | Path | None = None,
    business_risk_path: str | Path | None = None,
    thesis_status_path: str | Path | None = None,
    decision_record_path: str | Path | None = None,
    portfolio_audit_path: str | Path | None = None,
    memo_type: str = "investment_audit",
    mode: str = "analyst",
) -> dict[str, Any]:
    return build_investment_memo_package(
        audit_summary=load_json_artifact(audit_summary_path, required=True),
        explanations=load_json_artifact(explanations_path),
        sensitivity_summary=load_json_artifact(sensitivity_path),
        business_risk=load_json_artifact(business_risk_path),
        thesis_status=load_json_artifact(thesis_status_path),
        decision_record=load_json_artifact(decision_record_path),
        portfolio_audit=load_json_artifact(portfolio_audit_path),
        memo_type=memo_type,
        mode=mode,
    )


def investment_memo_to_files(
    output_dir: str | Path,
    *,
    audit_summary_path: str | Path,
    explanations_path: str | Path | None = None,
    sensitivity_path: str | Path | None = None,
    business_risk_path: str | Path | None = None,
    thesis_status_path: str | Path | None = None,
    decision_record_path: str | Path | None = None,
    portfolio_audit_path: str | Path | None = None,
    memo_type: str = "investment_audit",
    mode: str = "analyst",
) -> dict[str, Any]:
    package = investment_memo_from_files(
        audit_summary_path=audit_summary_path,
        explanations_path=explanations_path,
        sensitivity_path=sensitivity_path,
        business_risk_path=business_risk_path,
        thesis_status_path=thesis_status_path,
        decision_record_path=decision_record_path,
        portfolio_audit_path=portfolio_audit_path,
        memo_type=memo_type,
        mode=mode,
    )
    return {"package": package, "paths": write_investment_memo_artifacts(package, output_dir)}


def render_investment_memo_md(package: Mapping[str, Any]) -> str:
    sections = package.get("sections") or {}
    lines = [
        f"# Investment Research Audit Memo — {package.get('ticker', 'UNKNOWN')}",
        "",
        "## Verdict",
        "",
        f"- Status: `{package.get('status', 'UNKNOWN')}`",
        f"- Reason code: `{package.get('reason_code', 'UNKNOWN')}`",
        f"- Memo type: `{package.get('memo_type', 'investment_audit')}`",
        f"- Valuation date: `{package.get('valuation_date', 'UNKNOWN')}`",
        f"- Run ID: `{package.get('run_id') or 'UNKNOWN'}`",
        f"- Provider profile: `{package.get('provider_profile', 'UNKNOWN')}`",
        f"- Source quality: `{package.get('source_quality', 'UNKNOWN')}`",
        f"- Source class: `{package.get('source_class', 'UNKNOWN')}`",
        f"- Recommendation-language absent: `{package.get('recommendation_language_absent')}`",
        "",
        "## Executive audit view",
        "",
    ]
    for item in (sections.get("executive_audit_view") or {}).get("bullets") or []:
        lines.append(f"- {item}")
    lines += ["", "## Score and coverage", "", "| Axis | Score raw | Coverage pct | Known checks | UNKNOWN checks |", "|---|---:|---:|---:|---:|"]
    for row in (sections.get("score_and_coverage") or {}).get("rows") or []:
        lines.append(f"| `{row.get('axis')}` | {row.get('score_raw')} | {row.get('coverage_pct')} | {row.get('known_checks_count')} | {row.get('unknown_checks_count')} |")
    lines += ["", "## Data confidence", ""]
    data_conf = sections.get("data_confidence") or {}
    for key in ("level", "reason_code", "unknown_checks_count", "provider_degradation_visible"):
        lines.append(f"- {key}: `{data_conf.get(key, 'UNKNOWN')}`")
    lines += ["", "## Model applicability", ""]
    app = sections.get("model_applicability") or {}
    for key in ("status", "reason_code", "allowed_score_usage", "recommended_model"):
        lines.append(f"- {key}: `{app.get(key, 'UNKNOWN')}`")
    lines += ["", "## Conclusion risk", ""]
    risk = sections.get("conclusion_risk") or {}
    for key in ("risk_level", "reason_code"):
        lines.append(f"- {key}: `{risk.get(key, 'UNKNOWN')}`")
    for driver in risk.get("drivers") or []:
        lines.append(f"- Driver: {driver}")
    lines += ["", "## Sensitivity and valuation range", ""]
    sens = sections.get("sensitivity_and_valuation_range") or {}
    lines.append(f"- Status: `{sens.get('status', 'UNKNOWN')}`")
    lines.append(f"- Reason code: `{sens.get('reason_code', 'MEMO_COMPONENT_UNKNOWN')}`")
    lines.append(f"- Fragility level: `{sens.get('fragility_level', 'UNKNOWN')}`")
    lines += ["", "| Case | Fair value | Discount pct | Status |", "|---|---:|---:|---|"]
    for row in sens.get("valuation_range") or []:
        lines.append(f"| `{row.get('case')}` | {row.get('fair_value')} | {row.get('discount_pct')} | `{row.get('status')}` |")
    if not sens.get("valuation_range"):
        lines.append("| UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |")
    lines += ["", "## Business risk", ""]
    br = sections.get("business_risk") or {}
    lines.append(f"- Status: `{br.get('status', 'UNKNOWN')}`")
    lines.append(f"- Red flags count: `{br.get('red_flags_count', 'UNKNOWN')}`")
    lines.append(f"- Accounting quality: `{br.get('accounting_quality', 'UNKNOWN')}`")
    lines.append(f"- Capital allocation: `{br.get('capital_allocation', 'UNKNOWN')}`")
    for flag in br.get("top_red_flags") or []:
        lines.append(f"- Flag: `{flag}`")
    lines += ["", "## Thesis status", ""]
    thesis = sections.get("thesis_status") or {}
    lines.append(f"- Thesis status: `{thesis.get('thesis_status', 'UNKNOWN')}`")
    lines.append(f"- Reason code: `{thesis.get('reason_code', 'UNKNOWN')}`")
    lines.append(f"- Rules summary: `{thesis.get('rules_summary', {})}`")
    lines += ["", "## Decision context", ""]
    decision = sections.get("decision_context") or {}
    lines.append(f"- Status: `{decision.get('status', 'UNKNOWN')}`")
    lines.append(f"- Decision type: `{decision.get('decision_type', 'UNKNOWN')}`")
    lines.append(f"- Decision ID: `{decision.get('decision_id', 'UNKNOWN')}`")
    lines += ["", "## Portfolio context", ""]
    portfolio = sections.get("portfolio_context") or {}
    lines.append(f"- Status: `{portfolio.get('status', 'UNKNOWN')}`")
    lines.append(f"- Portfolio ID: `{portfolio.get('portfolio_id', 'UNKNOWN')}`")
    lines.append(f"- Holding weight pct: `{portfolio.get('holding_weight_pct', 'UNKNOWN')}`")
    lines.append(f"- Portfolio unknown exposure pct: `{portfolio.get('portfolio_unknown_exposure_pct', 'UNKNOWN')}`")
    lines += ["", "## What remains UNKNOWN / limited", ""]
    unknown = package.get("unknown_summary") or {}
    lines.append(f"- UNKNOWN checks count: `{unknown.get('unknown_checks_count', 0)}`")
    lines.append(f"- Missing optional components: `{', '.join((package.get('component_status') or {}).get('missing_components') or []) or 'none'}`")
    for item in unknown.get("critical_missing_inputs") or []:
        lines.append(f"- Critical missing input: `{item}`")
    for cluster in unknown.get("unknown_clusters") or []:
        lines.append(f"- UNKNOWN cluster: `{cluster}`")
    lines += ["", "## Manual review items", ""]
    for item in package.get("manual_review_items") or []:
        lines.append(f"- {item}")
    if not package.get("manual_review_items"):
        lines.append("- n/a")
    lines += ["", "## Limitations", ""]
    for limitation in package.get("limitations") or []:
        lines.append(f"- {limitation}")
    md = "\n".join(lines) + FOOTER
    _assert_no_recommendation_language(md)
    return md


def write_investment_memo_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = _safe_filename(str(package.get("ticker") or "UNKNOWN"))
    memo_type = _safe_filename(str(package.get("memo_type") or "investment_audit"))
    json_path = out / f"{ticker}_{memo_type}_memo.json"
    md_path = out / f"{ticker}_{memo_type}_memo.md"
    json_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_investment_memo_md(package), encoding="utf-8")
    return {"investment_memo_json": str(json_path), "investment_memo_md": str(md_path)}


def _unknown_memo(*, memo_type: str, mode: str) -> dict[str, Any]:
    return {
        "schema_version": "investment_memo.v0.1",
        "sprint": "v4.0-p0.11",
        "status": "UNKNOWN",
        "reason_code": "MEMO_INPUTS_MISSING",
        "ticker": "UNKNOWN",
        "exchange": "UNKNOWN",
        "valuation_date": "UNKNOWN",
        "memo_type": memo_type,
        "mode": mode,
        "component_status": {"present_components": [], "missing_components": ["audit_summary"], "reason_code": "MEMO_INPUTS_MISSING"},
        "sections": {},
        "unknown_summary": {"unknown_checks_count": 0, "critical_missing_inputs": ["audit_summary"], "unknown_clusters": []},
        "manual_review_items": ["Audit summary is required before a memo can be generated."],
        "recommendation_language_absent": True,
        "recommendation_guardrail": {"status": "PASS", "reason_code": "MEMO_NO_RECOMMENDATION_LANGUAGE", "recommendation_language_absent": True},
        "false_precision_guardrail": {"status": "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN"},
        "source_quality": "UNKNOWN",
        "source_class": "research_audit_memo",
        "input_lineage": {"audit_summary": "missing"},
        "limitations": ["No memo can be generated until audit_summary is supplied."],
        "not_investment_advice": True,
    }


def _component_status(audit: Mapping[str, Any], **components: Mapping[str, Any] | None) -> dict[str, Any]:
    present = ["audit_summary"]
    missing: list[str] = []
    for name, value in components.items():
        if value:
            present.append(name)
        else:
            missing.append(name)
    return {
        "status": "PASS_WITH_LIMITATIONS" if missing else "PASS",
        "reason_code": "MEMO_COMPONENT_UNKNOWN" if missing else "MEMO_GENERATED",
        "present_components": present,
        "missing_components": missing,
        "audit_summary_schema_version": audit.get("schema_version"),
    }


def _unknown_summary(audit: Mapping[str, Any], component_status: Mapping[str, Any]) -> dict[str, Any]:
    checks = audit.get("checks_summary") or {}
    critical = list(audit.get("critical_missing_inputs") or [])
    clusters = []
    for item in audit.get("unknown_clusters") or []:
        if isinstance(item, Mapping):
            clusters.append(str(item.get("reason_code") or item.get("cluster") or item))
        else:
            clusters.append(str(item))
    for comp in component_status.get("missing_components") or []:
        critical.append(f"optional_component_missing:{comp}")
    return {
        "status": "PASS_WITH_LIMITATIONS" if critical or checks.get("UNKNOWN", 0) else "PASS",
        "reason_code": "MEMO_UNKNOWN_PRESERVED" if critical or checks.get("UNKNOWN", 0) else "MEMO_GENERATED",
        "unknown_checks_count": int(checks.get("UNKNOWN") or 0),
        "critical_missing_inputs": sorted({str(x) for x in critical}),
        "unknown_clusters": sorted({str(x) for x in clusters}),
    }


def _executive_audit_view(audit: Mapping[str, Any], component_status: Mapping[str, Any], unknown_summary: Mapping[str, Any]) -> dict[str, Any]:
    data = audit.get("data_confidence") or {}
    app = audit.get("model_applicability") or {}
    risk = audit.get("conclusion_risk") or {}
    bullets = [
        f"Data confidence is `{data.get('level') or data.get('confidence_grade') or 'UNKNOWN'}`.",
        f"Model applicability is `{app.get('status', 'UNKNOWN')}` with score usage `{app.get('allowed_score_usage', 'UNKNOWN')}`.",
        f"Conclusion risk is `{risk.get('risk_level', 'UNKNOWN')}`.",
        f"UNKNOWN checks count is `{unknown_summary.get('unknown_checks_count', 0)}` and remains visible.",
    ]
    missing = component_status.get("missing_components") or []
    if missing:
        bullets.append(f"Optional memo components missing: {', '.join(missing)}.")
    return {"status": "PASS_WITH_LIMITATIONS", "reason_code": "MEMO_GENERATED", "bullets": bullets}


def _score_and_coverage_section(audit: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for axis, score in (audit.get("score_summary") or {}).items():
        rows.append({
            "axis": axis,
            "score_raw": score.get("score_raw"),
            "coverage_pct": score.get("coverage_pct"),
            "known_checks_count": score.get("known_checks_count"),
            "unknown_checks_count": score.get("unknown_checks_count"),
        })
    return {"status": "PASS" if rows else "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN" if not rows else "MEMO_GENERATED", "rows": rows}


def _data_confidence_section(audit: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(audit.get("data_confidence") or {})
    return {
        "status": data.get("status") or "PASS_WITH_LIMITATIONS",
        "reason_code": data.get("reason_code") or "MEMO_COMPONENT_UNKNOWN",
        "level": data.get("level") or data.get("confidence_grade") or "UNKNOWN",
        "unknown_checks_count": data.get("unknown_checks_count") or (audit.get("checks_summary") or {}).get("UNKNOWN", 0),
        "provider_degradation_visible": bool(audit.get("provider_degradation_visible") or data.get("provider_degradation_visible")),
        "critical_missing_inputs": list(audit.get("critical_missing_inputs") or data.get("critical_missing_inputs") or []),
    }


def _model_applicability_section(audit: Mapping[str, Any]) -> dict[str, Any]:
    app = audit.get("model_applicability") or {}
    return {
        "status": app.get("status") or "UNKNOWN",
        "reason_code": app.get("reason_code") or "MEMO_COMPONENT_UNKNOWN",
        "allowed_score_usage": app.get("allowed_score_usage") or "UNKNOWN",
        "recommended_model": app.get("recommended_model") or "UNKNOWN",
        "classification": app.get("classification") or app.get("company_classification") or "UNKNOWN",
    }


def _conclusion_risk_section(audit: Mapping[str, Any]) -> dict[str, Any]:
    risk = audit.get("conclusion_risk") or {}
    return {
        "status": risk.get("status") or "PASS_WITH_LIMITATIONS",
        "reason_code": risk.get("reason_code") or "MEMO_COMPONENT_UNKNOWN",
        "risk_level": risk.get("risk_level") or "UNKNOWN",
        "drivers": list(risk.get("drivers") or []),
        "manual_review_items": list(risk.get("manual_review_items") or []),
    }


def _sensitivity_section(sensitivity: Mapping[str, Any] | None) -> dict[str, Any]:
    if not sensitivity:
        return {"status": "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN", "fragility_level": "UNKNOWN", "valuation_range": []}
    valuation_rows = []
    for case, obj in (sensitivity.get("valuation_range") or {}).items():
        if isinstance(obj, Mapping):
            valuation_rows.append({
                "case": case,
                "fair_value": obj.get("fair_value"),
                "discount_pct": obj.get("discount_pct"),
                "status": obj.get("status") or "UNKNOWN",
            })
    frag = sensitivity.get("fragility") or {}
    return {
        "status": sensitivity.get("status") or "PASS_WITH_LIMITATIONS",
        "reason_code": sensitivity.get("reason_code") or "MEMO_FALSE_PRECISION_GUARDRAIL_APPLIED",
        "fragility_level": frag.get("fragility_level") or "UNKNOWN",
        "valuation_range": valuation_rows,
        "terminal_value_pct": (sensitivity.get("terminal_value_contribution") or {}).get("terminal_value_pct"),
        "reverse_dcf_status": (sensitivity.get("reverse_dcf") or {}).get("status") or "UNKNOWN",
    }


def _business_risk_section(business_risk: Mapping[str, Any] | None) -> dict[str, Any]:
    if not business_risk:
        return {"status": "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN", "red_flags_count": "UNKNOWN", "top_red_flags": []}
    red_summary = business_risk.get("red_flags_summary") or {}
    flags = []
    for flag in business_risk.get("red_flags") or []:
        if isinstance(flag, Mapping) and flag.get("result") == "FAIL":
            flags.append(str(flag.get("flag") or flag.get("reason_code") or "UNKNOWN"))
    return {
        "status": business_risk.get("status") or "PASS_WITH_LIMITATIONS",
        "reason_code": business_risk.get("reason_code") or "MEMO_GENERATED",
        "red_flags_count": red_summary.get("fail_count", len(flags)),
        "top_red_flags": flags[:5],
        "accounting_quality": (business_risk.get("accounting_quality") or {}).get("grade") or "UNKNOWN",
        "capital_allocation": (business_risk.get("capital_allocation") or {}).get("assessment") or "UNKNOWN",
    }


def _thesis_section(thesis: Mapping[str, Any] | None) -> dict[str, Any]:
    if not thesis:
        return {"status": "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN", "thesis_status": "UNKNOWN", "rules_summary": {}}
    return {
        "status": thesis.get("status") or "PASS_WITH_LIMITATIONS",
        "reason_code": thesis.get("reason_code") or "MEMO_GENERATED",
        "thesis_status": thesis.get("thesis_status") or "UNKNOWN",
        "rules_summary": thesis.get("rules_summary") or {},
        "manual_review_items": thesis.get("manual_review_items") or [],
    }


def _decision_section(decision: Mapping[str, Any] | None) -> dict[str, Any]:
    if not decision:
        return {"status": "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN", "decision_type": "UNKNOWN", "decision_id": "UNKNOWN"}
    return {
        "status": decision.get("status") or "UNKNOWN",
        "reason_code": decision.get("reason_code") or "MEMO_GENERATED",
        "decision_type": decision.get("decision_type") or "UNKNOWN",
        "decision_id": decision.get("decision_id") or "UNKNOWN",
        "review_date": decision.get("review_date") or "UNKNOWN",
    }


def _portfolio_context_section(portfolio: Mapping[str, Any] | None, ticker: str) -> dict[str, Any]:
    if not portfolio:
        return {"status": "UNKNOWN", "reason_code": "MEMO_COMPONENT_UNKNOWN", "portfolio_id": "UNKNOWN", "holding_weight_pct": "UNKNOWN"}
    holding = None
    for row in portfolio.get("holdings") or []:
        if str((row or {}).get("ticker") or "").upper() == ticker:
            holding = row
            break
    return {
        "status": portfolio.get("status") or "PASS_WITH_LIMITATIONS",
        "reason_code": portfolio.get("reason_code") or "MEMO_GENERATED",
        "portfolio_id": portfolio.get("portfolio_id") or "UNKNOWN",
        "holding_weight_pct": (holding or {}).get("weight_pct", "UNKNOWN"),
        "portfolio_unknown_exposure_pct": (portfolio.get("unknown_exposure") or {}).get("weight_pct", "UNKNOWN"),
        "portfolio_weighted_conclusion_risk": (portfolio.get("weighted_conclusion_risk") or {}).get("level", "UNKNOWN"),
    }


def _unknown_limitations_section(audit: Mapping[str, Any], unknown_summary: Mapping[str, Any], component_status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": unknown_summary.get("status"),
        "reason_code": unknown_summary.get("reason_code"),
        "unknown_checks_count": unknown_summary.get("unknown_checks_count"),
        "critical_missing_inputs": list(unknown_summary.get("critical_missing_inputs") or []),
        "unknown_clusters": list(unknown_summary.get("unknown_clusters") or []),
        "missing_components": list(component_status.get("missing_components") or []),
        "warnings_count": len(audit.get("warnings") or []),
    }


def _manual_review_items(audit: Mapping[str, Any], component_status: Mapping[str, Any], *, sensitivity_summary: Mapping[str, Any] | None, business_risk: Mapping[str, Any] | None, thesis_status: Mapping[str, Any] | None, portfolio_audit: Mapping[str, Any] | None) -> list[str]:
    items: list[str] = []
    data = audit.get("data_confidence") or {}
    app = audit.get("model_applicability") or {}
    risk = audit.get("conclusion_risk") or {}
    if data.get("level") in {"LOW", "UNKNOWN"} or data.get("confidence_grade") in {"D", "E"}:
        items.append("Data confidence is LOW/UNKNOWN; review source lineage before using this memo.")
    if audit.get("provider_degradation_visible"):
        items.append("Provider degradation is visible in the audit summary.")
    if app.get("status") in {"DEGRADED", "NOT_APPLICABLE", "UNKNOWN"}:
        items.append(f"Model applicability requires review: {app.get('status')}/{app.get('allowed_score_usage')}." )
    if risk.get("risk_level") in {"HIGH", "UNKNOWN"}:
        items.append(f"Conclusion risk requires review: {risk.get('risk_level')}.")
    if (business_risk or {}).get("red_flags_summary", {}).get("fail_count", 0):
        items.append("Business-risk red flags are present.")
    if (thesis_status or {}).get("thesis_status") in {"WATCH", "BROKEN", "UNKNOWN"}:
        items.append(f"Thesis status requires review: {(thesis_status or {}).get('thesis_status')}.")
    if sensitivity_summary and (sensitivity_summary.get("fragility") or {}).get("fragility_level") in {"HIGH", "UNKNOWN"}:
        items.append("Sensitivity fragility is HIGH/UNKNOWN.")
    if portfolio_audit and (portfolio_audit.get("unknown_exposure") or {}).get("weight_pct", 0):
        items.append("Portfolio context includes UNKNOWN exposure.")
    for comp in component_status.get("missing_components") or []:
        items.append(f"Optional component missing: {comp}.")
    for item in audit.get("critical_missing_inputs") or []:
        items.append(f"Critical missing input remains visible: {item}.")
    return sorted({str(i) for i in items})


def _false_precision_guardrail(sensitivity: Mapping[str, Any] | None) -> dict[str, Any]:
    if not sensitivity:
        return {
            "status": "UNKNOWN",
            "reason_code": "MEMO_COMPONENT_UNKNOWN",
            "policy": "No point fair-value conclusion is displayed without a sensitivity/valuation-range artifact.",
            "valuation_range_present": False,
        }
    has_range = bool(sensitivity.get("valuation_range"))
    return {
        "status": "PASS" if has_range else "PASS_WITH_LIMITATIONS",
        "reason_code": "MEMO_FALSE_PRECISION_GUARDRAIL_APPLIED",
        "policy": "Fair value is shown as a range when available; point-only conclusions are not promoted.",
        "valuation_range_present": has_range,
    }


def _recommendation_guardrail(sections: Mapping[str, Any]) -> dict[str, Any]:
    text = json.dumps(sections, sort_keys=True)
    found = [token for token in FORBIDDEN_RECOMMENDATION_TOKENS if token in text]
    return {
        "status": "PASS" if not found else "FAIL",
        "reason_code": "MEMO_NO_RECOMMENDATION_LANGUAGE" if not found else "MEMO_RECOMMENDATION_LANGUAGE_REJECTED",
        "recommendation_language_absent": not found,
        "forbidden_tokens_found": found,
    }


def _assert_no_recommendation_language(text: str) -> None:
    found = [token for token in FORBIDDEN_RECOMMENDATION_TOKENS if token in text]
    if found:
        raise ValueError(f"Memo contains forbidden recommendation-language tokens: {found}")


def _aggregate_source_quality(*artifacts: Mapping[str, Any] | None) -> str:
    rank = {"HIGH": 5, "MEDIUM_HIGH": 4, "MEDIUM": 3, "MEDIUM_LOW": 2, "LOW": 1, "UNKNOWN": 0, "exact": 5, "approximation": 3, "assumption": 2, "missing": 0}
    values = [str((a or {}).get("source_quality") or "UNKNOWN") for a in artifacts if a]
    if not values:
        return "UNKNOWN"
    return min(values, key=lambda v: rank.get(v, 0))


def _aggregate_source_class(*artifacts: Mapping[str, Any] | None) -> str:
    classes = sorted({str((a or {}).get("source_class") or "research_audit_artifact") for a in artifacts if a})
    return ",".join(classes) if classes else "research_audit_memo"


def _artifact_lineage(artifact: Mapping[str, Any] | None) -> dict[str, Any] | str:
    if not artifact:
        return "missing"
    return {
        "schema_version": artifact.get("schema_version"),
        "ticker": artifact.get("ticker"),
        "run_id": artifact.get("run_id"),
        "source_quality": artifact.get("source_quality"),
        "source_class": artifact.get("source_class"),
    }


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned or "UNKNOWN"
