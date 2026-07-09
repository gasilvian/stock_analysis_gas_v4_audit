"""Template-driven explanations for checks and audit artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from sws_engine.explain.dictionary import get_reason_template, load_reason_code_dictionary

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)


def _summarize_mapping(value: Any, *, max_items: int = 8) -> str:
    if not value:
        return "none"
    if isinstance(value, dict):
        parts = []
        for idx, (key, item) in enumerate(value.items()):
            if idx >= max_items:
                parts.append("...")
                break
            parts.append(f"{key}={item}")
        return ", ".join(parts) if parts else "none"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value[:max_items]) or "none"
    return str(value)


def _safe_format(template: str, context: Mapping[str, Any]) -> str:
    class SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "UNKNOWN"

    try:
        return template.format_map(SafeDict({k: "UNKNOWN" if v is None else v for k, v in context.items()}))
    except Exception:
        return template


def explain_check(
    check: Mapping[str, Any],
    *,
    mode: str = "analyst",
    dictionary: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    dictionary = dictionary or load_reason_code_dictionary()
    reason_code = str(check.get("reason_code") or "UNKNOWN")
    template = get_reason_template(dictionary, reason_code)
    selected_mode = "plain_english" if mode == "plain_english" else "analyst"
    context = {
        "axis": check.get("axis") or "UNKNOWN",
        "check_id": check.get("id") or "UNKNOWN",
        "check_name": check.get("name") or "UNKNOWN",
        "result": check.get("result") or "UNKNOWN",
        "reason_code": reason_code,
        "source_quality": check.get("source_quality") or "UNKNOWN",
        "source_class": check.get("source_class") or "UNKNOWN",
        "inputs_summary": _summarize_mapping(check.get("inputs") or {}),
        "threshold": check.get("threshold") or "none",
        "lineage_summary": _summarize_mapping(check.get("input_lineage") or {}),
        "unknown_checks_count": check.get("unknown_checks_count") or "UNKNOWN",
    }
    explanation = _safe_format(str(template[selected_mode]), context)
    return {
        "axis": context["axis"],
        "check_id": context["check_id"],
        "check_name": context["check_name"],
        "result": context["result"],
        "reason_code": reason_code,
        "severity": template["severity"],
        "mode": selected_mode,
        "explanation": explanation,
        "remediation_hint": _safe_format(str(template["remediation_hint"]), context),
        "source_quality": context["source_quality"],
        "source_class": context["source_class"],
        "input_lineage": check.get("input_lineage") or {},
        "known_reason_code": template["known_reason_code"],
    }


def explain_checks(
    output: Mapping[str, Any],
    *,
    mode: str = "analyst",
    include_pass: bool = False,
    result_filter: Iterable[str] | None = None,
    dictionary: Mapping[str, Any] | None = None,
) -> list[Dict[str, Any]]:
    dictionary = dictionary or load_reason_code_dictionary()
    allowed = set(result_filter or ([] if include_pass else ["FAIL", "UNKNOWN"]))
    explanations: list[Dict[str, Any]] = []
    for check in output.get("checks") or []:
        if not isinstance(check, dict):
            continue
        result = str(check.get("result") or "UNKNOWN")
        if include_pass or not allowed or result in allowed:
            explanations.append(explain_check(check, mode=mode, dictionary=dictionary))
    return explanations


def _explain_reason_items(
    items: Iterable[Mapping[str, Any]],
    *,
    mode: str,
    dictionary: Mapping[str, Any],
    source: str,
) -> list[Dict[str, Any]]:
    out: list[Dict[str, Any]] = []
    for item in items:
        reason_code = str(item.get("reason_code") or item.get("id") or "UNKNOWN")
        fake_check = {
            "axis": source,
            "id": item.get("id") or reason_code,
            "name": item.get("name") or source,
            "result": item.get("result") or item.get("status") or "UNKNOWN",
            "reason_code": reason_code,
            "source_quality": item.get("source_quality") or "approximation",
            "source_class": item.get("source_class") or "E3",
            "inputs": item,
            "threshold": item.get("threshold") or "n/a",
            "input_lineage": item.get("input_lineage") or {},
            "unknown_checks_count": item.get("unknown_checks_count"),
        }
        rec = explain_check(fake_check, mode=mode, dictionary=dictionary)
        rec["source_component"] = source
        out.append(rec)
    return out


def explain_audit_summary(
    audit_summary: Mapping[str, Any],
    *,
    mode: str = "analyst",
    dictionary: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    dictionary = dictionary or load_reason_code_dictionary()
    reason_items: list[Dict[str, Any]] = []
    data_conf = audit_summary.get("data_confidence") or {}
    for code in data_conf.get("reason_codes") or []:
        reason_items.append({"reason_code": code, "status": data_conf.get("status"), "unknown_checks_count": data_conf.get("unknown_checks_count")})
    model = audit_summary.get("model_applicability") or {}
    if model.get("reason_code"):
        reason_items.append({"reason_code": model.get("reason_code"), "status": model.get("status"), **model})
    risk = audit_summary.get("conclusion_risk") or {}
    reason_items.extend(risk.get("drivers") or [])
    return {
        "data_confidence_explanations": _explain_reason_items(reason_items, mode=mode, dictionary=dictionary, source="audit"),
        "unknown_cluster_explanations": _explain_reason_items(audit_summary.get("unknown_clusters") or [], mode=mode, dictionary=dictionary, source="unknown_cluster"),
        "manual_review_items": risk.get("manual_review_items") or [],
    }


def build_explanation_package(
    output: Mapping[str, Any],
    *,
    audit_summary: Mapping[str, Any] | None = None,
    mode: str = "analyst",
    include_pass: bool = False,
    dictionary_path: str | Path | None = None,
) -> Dict[str, Any]:
    dictionary = load_reason_code_dictionary(dictionary_path)
    check_explanations = explain_checks(output, mode=mode, include_pass=include_pass, dictionary=dictionary)
    audit_explanations = explain_audit_summary(audit_summary or {}, mode=mode, dictionary=dictionary) if audit_summary else {}
    unknown_count = sum(1 for c in output.get("checks") or [] if isinstance(c, dict) and c.get("result") == "UNKNOWN")
    fail_count = sum(1 for c in output.get("checks") or [] if isinstance(c, dict) and c.get("result") == "FAIL")
    return {
        "schema_version": "explanation_package.v0.1",
        "ticker": output.get("ticker", "UNKNOWN"),
        "exchange": output.get("exchange", "UNKNOWN"),
        "valuation_date": output.get("valuation_date", "UNKNOWN"),
        "provider_profile": output.get("provider_profile", "UNKNOWN"),
        "mode": "plain_english" if mode == "plain_english" else "analyst",
        "include_pass": include_pass,
        "checks_explained_count": len(check_explanations),
        "unknown_checks_count": unknown_count,
        "fail_checks_count": fail_count,
        "check_explanations": check_explanations,
        "audit_explanations": audit_explanations,
        "dictionary_version": (dictionary.get("metadata") or {}).get("version"),
        "known_reason_codes_complete_for_package": all(e.get("known_reason_code") for e in check_explanations),
        "not_investment_advice": True,
    }


def explanation_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        f"# Explanation Report — {package.get('ticker', 'UNKNOWN')}",
        "",
        "## Scope",
        "",
        "This is a deterministic reason-code explanation report. It is not investment advice.",
        "",
        f"- Mode: `{package.get('mode', 'analyst')}`",
        f"- Provider profile: `{package.get('provider_profile', 'UNKNOWN')}`",
        f"- Dictionary version: `{package.get('dictionary_version', 'UNKNOWN')}`",
        f"- Checks explained: `{package.get('checks_explained_count', 0)}`",
        f"- UNKNOWN checks: `{package.get('unknown_checks_count', 0)}`",
        f"- FAIL checks: `{package.get('fail_checks_count', 0)}`",
        "",
        "## Check explanations",
        "",
    ]
    explanations = package.get("check_explanations") or []
    if not explanations:
        lines.append("No FAIL/UNKNOWN checks were selected for explanation.")
    else:
        for exp in explanations:
            lines += [
                f"### {exp.get('axis')}/{exp.get('check_id')} — {exp.get('check_name')}",
                "",
                f"- Result: `{exp.get('result')}`",
                f"- Reason code: `{exp.get('reason_code')}`",
                f"- Severity: `{exp.get('severity')}`",
                f"- Source quality/class: `{exp.get('source_quality')}` / `{exp.get('source_class')}`",
                f"- Explanation: {exp.get('explanation')}",
                f"- Remediation: {exp.get('remediation_hint')}",
                "",
            ]
    audit = package.get("audit_explanations") or {}
    audit_exps = audit.get("data_confidence_explanations") or []
    if audit_exps:
        lines += ["## Audit driver explanations", ""]
        for exp in audit_exps:
            lines += [
                f"- `{exp.get('reason_code')}` [{exp.get('severity')}]: {exp.get('explanation')} Remediation: {exp.get('remediation_hint')}",
            ]
    manual_items = audit.get("manual_review_items") or []
    if manual_items:
        lines += ["", "## Manual review items", ""]
        lines.extend(f"- {item}" for item in manual_items)
    return "\n".join(lines) + FOOTER


def write_explanation_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(package.get("ticker") or "UNKNOWN")
    mode = str(package.get("mode") or "analyst")
    json_path = out / f"{ticker}_explanations_{mode}.json"
    md_path = out / f"{ticker}_explanation_report_{mode}.md"
    json_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(explanation_report_md(package), encoding="utf-8")
    return {"explanations_json": str(json_path), "explanation_report_md": str(md_path)}
