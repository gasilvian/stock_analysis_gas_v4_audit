"""Sensitivity artifact writer and Markdown report."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from sws_engine.audit.audit_summary import load_latest_audit_context_from_db, write_json
from sws_engine.config.assumptions_loader import load_assumptions
from sws_engine.sensitivity.scenario_runner import run_sensitivity

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)


def sensitivity_report_md(summary: Dict[str, Any]) -> str:
    lines = [
        f"# Sensitivity Report — {summary.get('ticker', 'UNKNOWN')}",
        "",
        "## Audit verdict, not investment advice",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Reason code: `{summary.get('reason_code')}`",
        f"- Valuation date: `{summary.get('valuation_date') or 'UNKNOWN'}`",
        f"- Run ID: `{summary.get('run_id') or 'UNKNOWN'}`",
        f"- Source quality: `{summary.get('source_quality')}`",
        f"- Source class: `{summary.get('source_class')}`",
        "",
        "## Base case",
        "",
    ]
    base = summary.get("base_case") or {}
    lines += [
        f"- Fair value: `{base.get('fair_value')}`",
        f"- Discount pct: `{base.get('discount_pct')}`",
        f"- Valuation model: `{base.get('valuation_model')}`",
        f"- Valuation variant: `{base.get('valuation_variant')}`",
        "",
        "## Valuation range",
        "",
        "| Case | Fair value | Discount pct | DR delta bps | g delta bps | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for label, case in (summary.get("valuation_range") or {}).items():
        lines.append(
            f"| {label} | {case.get('fair_value')} | {case.get('discount_pct')} | "
            f"{case.get('discount_rate_bps_delta')} | {case.get('terminal_growth_bps_delta')} | {case.get('status')} |"
        )
    lines += [
        "",
        "## Fragility",
        "",
    ]
    frag = summary.get("fragility") or {}
    lines += [
        f"- Fragility level: **{frag.get('fragility_level', 'UNKNOWN')}**",
        f"- Spread pct of base: `{frag.get('spread_pct_of_base')}`",
        f"- Reason code: `{frag.get('reason_code')}`",
        "",
        "## Terminal value contribution",
        "",
    ]
    tv = summary.get("terminal_value_contribution") or {}
    lines += [
        f"- Status: `{tv.get('status')}`",
        f"- Terminal value pct: `{tv.get('terminal_value_pct')}`",
        f"- Is TV dominated: `{tv.get('is_terminal_value_dominated')}`",
        "",
        "## Reverse DCF",
        "",
    ]
    rd = summary.get("reverse_dcf") or {}
    lines += [
        f"- Status: `{rd.get('status')}`",
        f"- Reason code: `{rd.get('reason_code')}`",
        f"- Implied base growth: `{rd.get('implied_base_growth')}`",
        "",
        "## Scenario matrix",
        "",
        "| DR delta bps | g delta bps | Fair value | Status | Reason |",
        "|---:|---:|---:|---|---|",
    ]
    for row in summary.get("scenario_matrix") or []:
        lines.append(
            f"| {row.get('discount_rate_bps_delta')} | {row.get('terminal_growth_bps_delta')} | "
            f"{row.get('fair_value')} | {row.get('status')} | `{row.get('reason_code')}` |"
        )
    warnings = summary.get("warnings") or []
    lines += ["", "## Warnings", ""]
    lines.extend(f"- `{w}`" for w in warnings) if warnings else lines.append("No sensitivity warnings.")
    return "\n".join(lines) + FOOTER


def write_sensitivity_artifacts(summary: Dict[str, Any], output_dir: str | Path) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(summary.get("ticker", "UNKNOWN"))
    run_id = str(summary.get("run_id") or "input")
    json_path = out / f"{ticker}_sensitivity_summary_{run_id}.json"
    md_path = out / f"{ticker}_sensitivity_report_{run_id}.md"
    write_json(json_path, summary)
    md_path.write_text(sensitivity_report_md(summary), encoding="utf-8")
    return {"sensitivity_summary_json": str(json_path), "sensitivity_report_md": str(md_path)}


def sensitivity_company_to_files(
    output_dir: str | Path,
    *,
    input_path: str | None = None,
    db_path: str | None = None,
    ticker: str | None = None,
    run_id: str | None = None,
    assumptions_path: str = "config/assumptions.yaml",
    sensitivity_config_path: str = "config/sensitivity.yaml",
) -> Dict[str, Any]:
    assumptions = load_assumptions(assumptions_path)
    if input_path:
        payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
        base_output = None
        effective_run_id = run_id
    else:
        if not db_path or not ticker:
            raise ValueError("Either --input or both --db and --ticker are required.")
        ctx = load_latest_audit_context_from_db(db_path, ticker, run_id=run_id)
        if not ctx.get("input_payload"):
            raise FileNotFoundError(f"No input payload snapshot found for ticker '{ticker}'.")
        payload = ctx["input_payload"]
        base_output = ctx.get("output")
        effective_run_id = ctx.get("run_id")
    summary = run_sensitivity(
        payload,
        assumptions,
        policy_path=sensitivity_config_path,
        run_id=effective_run_id,
        base_output=base_output,
    )
    paths = write_sensitivity_artifacts(summary, output_dir)
    return {"summary": summary, "paths": paths}
