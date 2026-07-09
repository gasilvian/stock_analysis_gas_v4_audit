"""Markdown reporting for audit_summary v0.1."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sws_engine.audit.audit_summary import build_audit_summary_from_db, write_json
from sws_engine.explain.check_explainer import explain_checks

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)


def audit_report_md(summary: Dict[str, Any]) -> str:
    dc = summary.get("data_confidence", {})
    ma = summary.get("model_applicability", {})
    cr = summary.get("conclusion_risk", {})
    lines: list[str] = [
        f"# Audit Report — {summary.get('ticker', 'UNKNOWN')}",
        "",
        "## Audit verdict, not investment advice",
        "",
        f"- Ticker: `{summary.get('ticker', 'UNKNOWN')}`",
        f"- Exchange: `{summary.get('exchange', 'UNKNOWN')}`",
        f"- Valuation date: `{summary.get('valuation_date', 'UNKNOWN')}`",
        f"- Provider profile: `{summary.get('provider_profile', 'UNKNOWN')}`",
        f"- Run ID: `{summary.get('run_id') or 'UNKNOWN'}`",
        f"- Input snapshot ID: `{summary.get('input_snapshot_id') or 'UNKNOWN'}`",
        f"- Engine version: `{summary.get('engine_version', 'UNKNOWN')}`",
        f"- Assumptions hash: `{summary.get('assumptions_hash') or 'UNKNOWN'}`",
        "",
        "## Audit summary",
        "",
        f"- Data confidence: **{dc.get('level', 'UNKNOWN')}** / grade `{dc.get('confidence_grade', 'UNKNOWN')}`",
        f"- Model applicability: **{ma.get('status', 'UNKNOWN')}** (`{ma.get('reason_code', 'UNKNOWN')}`)",
        f"- Allowed score usage: `{ma.get('allowed_score_usage', 'UNKNOWN')}`",
        f"- Conclusion risk: **{cr.get('risk_level', 'UNKNOWN')}**",
        f"- Provider degradation visible: `{summary.get('provider_degradation_visible')}`",
        "",
        "## Score and coverage",
        "",
        "| Axis | score_raw | coverage_pct | known | unknown |",
        "|---|---:|---:|---:|---:|",
    ]
    for axis, score in sorted((summary.get("score_summary") or {}).items()):
        lines.append(
            f"| {axis} | {score.get('score_raw')} | {score.get('coverage_pct')} | "
            f"{score.get('known_checks_count')} | {score.get('unknown_checks_count')} |"
        )

    lines += [
        "",
        "## What we don't know",
        "",
    ]
    missing = summary.get("critical_missing_inputs") or []
    clusters = summary.get("unknown_clusters") or []
    if not missing and not clusters:
        lines.append("No UNKNOWN checks or critical missing inputs were detected by the audit layer.")
    if missing:
        lines += ["### Critical missing inputs", "", "| Field | Criticality | Checks affected | Remediation |", "|---|---|---:|---|"]
        for item in missing:
            lines.append(
                f"| `{item.get('field')}` | {item.get('criticality')} | "
                f"{item.get('checks_affected_count')} | {item.get('remediation_hint')} |"
            )
    if clusters:
        lines += ["", "### UNKNOWN clusters", "", "| Reason code | Count |", "|---|---:|"]
        for cluster in clusters:
            lines.append(f"| `{cluster.get('reason_code')}` | {cluster.get('count')} |")

    lines += [
        "",
        "## Source quality mix",
        "",
        "| source_quality | count |",
        "|---|---:|",
    ]
    for key, value in (dc.get("source_quality_mix") or {}).items():
        lines.append(f"| `{key}` | {value} |")
    lines += ["", "## Source class mix", "", "| source_class | count |", "|---|---:|"]
    for key, value in (dc.get("source_class_mix") or {}).items():
        lines.append(f"| `{key}` | {value} |")

    lines += ["", "## Conclusion risk drivers", ""]
    for driver in cr.get("drivers") or []:
        lines.append(f"- `{driver.get('reason_code')}` — impact `{driver.get('risk_impact')}`")
    review_items = cr.get("manual_review_items") or []
    lines += ["", "## Manual review items", ""]
    if review_items:
        lines.extend(f"- {item}" for item in review_items)
    else:
        lines.append("No mandatory manual review item was produced by P0.1 rules.")

    # P0.6 Explainability: render deterministic explanations for FAIL/UNKNOWN
    # checks when the original checks are available in the summary lineage. If
    # not present, the audit report still remains valid and honest.
    output_lineage = (summary.get("lineage") or {}).get("output_lineage") or {}
    original_output = summary.get("original_output") or output_lineage.get("output") or {}
    check_explanations = explain_checks(original_output, mode="analyst") if original_output.get("checks") else []
    lines += ["", "## Check explanations", ""]
    if check_explanations:
        for exp in check_explanations:
            lines.append(
                f"- `{exp.get('axis')}/{exp.get('check_id')}` `{exp.get('reason_code')}` "
                f"[{exp.get('severity')}]: {exp.get('explanation')} "
                f"Remediation: {exp.get('remediation_hint')}"
            )
    else:
        lines.append("No FAIL/UNKNOWN checks were available for P0.6 explanation rendering.")

    warnings = summary.get("warnings") or []
    lines += ["", "## Warnings", ""]
    if warnings:
        lines.extend(f"- `{warning}`" for warning in warnings)
    else:
        lines.append("No warnings in source output or audit layer.")

    return "\n".join(lines) + FOOTER


def write_audit_artifacts(summary: Dict[str, Any], output_dir: str | Path) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(summary.get("ticker", "UNKNOWN"))
    run_id = str(summary.get("run_id") or "latest")
    json_path = out / f"{ticker}_audit_summary_{run_id}.json"
    md_path = out / f"{ticker}_audit_report_{run_id}.md"
    write_json(json_path, summary)
    md_path.write_text(audit_report_md(summary), encoding="utf-8")
    return {"audit_summary_json": str(json_path), "audit_report_md": str(md_path)}


def audit_company_from_db_to_files(
    db_path: str,
    ticker: str,
    output_dir: str | Path,
    run_id: str | None = None,
    *,
    audit_policies_path: str | None = None,
    source_registry_path: str | None = None,
    identifier_master_path: str | None = None,
) -> Dict[str, Any]:
    summary = build_audit_summary_from_db(
        db_path,
        ticker,
        run_id=run_id,
        audit_policies_path=audit_policies_path,
        source_registry_path=source_registry_path,
        identifier_master_path=identifier_master_path,
    )
    paths = write_audit_artifacts(summary, output_dir)
    return {"summary": summary, "paths": paths}
