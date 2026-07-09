"""P0.9 Thesis Tracker foundation.

This module evaluates local thesis YAML files against existing audit artifacts.
It never fetches market data, never changes the canonical output schema, and
returns UNKNOWN for unevaluable rules instead of inventing values.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

STATUS_ON_TRACK = "ON_TRACK"
STATUS_WATCH = "WATCH"
STATUS_BROKEN = "BROKEN"
STATUS_UNKNOWN = "UNKNOWN"

VALID_THESIS_STATUSES = {STATUS_ON_TRACK, STATUS_WATCH, STATUS_BROKEN, STATUS_UNKNOWN}


def load_thesis(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Thesis file not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Thesis YAML must parse to a mapping")
    return data


def load_json_artifact(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Artifact not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Artifact must be a JSON object: {p}")
    return data


def evaluate_thesis(
    thesis: Mapping[str, Any] | None,
    *,
    audit_summary: Mapping[str, Any] | None = None,
    business_risk: Mapping[str, Any] | None = None,
    sensitivity_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a local thesis against supplied audit artifacts.

    Input rules are deliberately simple dictionaries with `source_field`,
    `operator` and `threshold`/`value`. Missing paths produce UNKNOWN rule
    results and degrade thesis status; they are not ignored.
    """
    thesis_obj = dict(thesis or {})
    if not thesis_obj:
        return _unknown_package("UNKNOWN", "THESIS_INPUTS_MISSING", "UNKNOWN", [], [], ["Provide a thesis YAML/JSON object."])
    ticker = str(thesis_obj.get("ticker") or _safe_get(audit_summary, "ticker") or "UNKNOWN").upper()
    context = _build_context(audit_summary, business_risk, sensitivity_summary)
    invalidation_rules = _normalize_rules(thesis_obj.get("invalidation_rules") or [], category="invalidation")
    watch_metrics = _normalize_rules(thesis_obj.get("watch_metrics") or [], category="watch_metric")

    evaluated_invalidation = [_evaluate_rule(rule, context) for rule in invalidation_rules]
    evaluated_watch = [_evaluate_rule(rule, context) for rule in watch_metrics]
    all_rules = evaluated_invalidation + evaluated_watch

    manual_review_items: list[str] = []
    for rule in all_rules:
        if rule["result"] == "UNKNOWN":
            manual_review_items.append(f"Rule `{rule['id']}` could not be evaluated: {rule['reason_code']}")
        elif rule["result"] == "TRIGGERED":
            manual_review_items.append(f"Rule `{rule['id']}` is triggered and requires review.")

    if not all_rules:
        thesis_status = STATUS_UNKNOWN
        status = "UNKNOWN"
        reason_code = "THESIS_NO_EVALUABLE_RULES"
        manual_review_items.append("No watch_metrics or invalidation_rules were supplied.")
    else:
        triggered_invalidation = [r for r in evaluated_invalidation if r["result"] == "TRIGGERED"]
        triggered_watch = [r for r in evaluated_watch if r["result"] == "TRIGGERED"]
        unknown_rules = [r for r in all_rules if r["result"] == "UNKNOWN"]
        if triggered_invalidation:
            thesis_status = STATUS_BROKEN
            reason_code = "THESIS_INVALIDATION_TRIGGERED"
        elif len(unknown_rules) > (len(all_rules) / 2):
            thesis_status = STATUS_UNKNOWN
            reason_code = "THESIS_MAJORITY_RULES_UNKNOWN"
        elif triggered_watch:
            thesis_status = STATUS_WATCH
            reason_code = "THESIS_WATCH_METRIC_TRIGGERED"
        elif unknown_rules:
            thesis_status = STATUS_WATCH
            reason_code = "THESIS_RULES_PARTIALLY_UNKNOWN"
        else:
            thesis_status = STATUS_ON_TRACK
            reason_code = "THESIS_ON_TRACK"
        status = "PASS_WITH_LIMITATIONS" if thesis_status in {STATUS_ON_TRACK, STATUS_WATCH, STATUS_BROKEN} else "UNKNOWN"

    package = {
        "schema_version": "thesis_status.v0.1",
        "sprint": "v4.0-p0.9",
        "status": status,
        "reason_code": reason_code,
        "ticker": ticker,
        "thesis_status": thesis_status,
        "thesis_type": thesis_obj.get("thesis_type") or thesis_obj.get("type") or "UNKNOWN",
        "created_at": _json_scalar(thesis_obj.get("created_at")),
        "review_cadence": _json_scalar(thesis_obj.get("review_cadence")),
        "next_review_date": _json_scalar(thesis_obj.get("next_review_date")),
        "bull_case": list(thesis_obj.get("bull_case") or []),
        "bear_case": list(thesis_obj.get("bear_case") or []),
        "watch_metrics": evaluated_watch,
        "invalidation_rules": evaluated_invalidation,
        "rules_summary": _rules_summary(all_rules),
        "manual_review_items": manual_review_items,
        "source_quality": _source_quality(audit_summary, business_risk, sensitivity_summary),
        "source_class": _source_class(audit_summary, business_risk, sensitivity_summary),
        "input_lineage": {
            "thesis": "operator_curated_local_file_or_api_payload",
            "audit_summary_present": audit_summary is not None,
            "business_risk_present": business_risk is not None,
            "sensitivity_summary_present": sensitivity_summary is not None,
        },
        "limitations": [
            "P0.9 evaluates only machine-readable thesis rules supplied by the operator.",
            "Unevaluable rules become UNKNOWN and degrade thesis status; they are not ignored.",
            "Thesis status is research process hygiene, not investment advice and not buy/sell/hold guidance.",
        ],
        "not_investment_advice": True,
    }
    return package


def evaluate_thesis_from_files(
    thesis_path: str | Path,
    *,
    audit_summary_path: str | Path | None = None,
    business_risk_path: str | Path | None = None,
    sensitivity_path: str | Path | None = None,
) -> dict[str, Any]:
    return evaluate_thesis(
        load_thesis(thesis_path),
        audit_summary=load_json_artifact(audit_summary_path),
        business_risk=load_json_artifact(business_risk_path),
        sensitivity_summary=load_json_artifact(sensitivity_path),
    )


def thesis_status_to_files(
    thesis_path: str | Path,
    output_dir: str | Path,
    *,
    audit_summary_path: str | Path | None = None,
    business_risk_path: str | Path | None = None,
    sensitivity_path: str | Path | None = None,
) -> dict[str, Any]:
    package = evaluate_thesis_from_files(
        thesis_path,
        audit_summary_path=audit_summary_path,
        business_risk_path=business_risk_path,
        sensitivity_path=sensitivity_path,
    )
    paths = write_thesis_artifacts(package, output_dir)
    return {"package": package, "paths": paths}


def write_thesis_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(package.get("ticker") or "UNKNOWN"))
    json_path = out / f"{ticker}_thesis_status.json"
    md_path = out / f"{ticker}_thesis_status_report.md"
    json_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_thesis_report_md(package), encoding="utf-8")
    return {"thesis_status_json": str(json_path), "thesis_status_report_md": str(md_path)}


def render_thesis_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        "# Thesis Status Report",
        "",
        "## Verdict",
        "",
        f"- Ticker: `{package.get('ticker', 'UNKNOWN')}`",
        f"- Status: `{package.get('status', 'UNKNOWN')}`",
        f"- Reason code: `{package.get('reason_code', 'UNKNOWN')}`",
        f"- Thesis status: `{package.get('thesis_status', 'UNKNOWN')}`",
        f"- Thesis type: `{package.get('thesis_type', 'UNKNOWN')}`",
        "",
        "## Rule summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in (package.get("rules_summary") or {}).items():
        lines.append(f"| {key} | {value} |")
    lines += ["", "## Invalidation rules", "", "| Rule | Result | Reason code | Current value | Threshold |", "|---|---|---|---:|---:|"]
    for rule in package.get("invalidation_rules") or []:
        lines.append(_rule_row(rule))
    if not package.get("invalidation_rules"):
        lines.append("| n/a | UNKNOWN | THESIS_NO_EVALUABLE_RULES | n/a | n/a |")
    lines += ["", "## Watch metrics", "", "| Rule | Result | Reason code | Current value | Threshold |", "|---|---|---|---:|---:|"]
    for rule in package.get("watch_metrics") or []:
        lines.append(_rule_row(rule))
    if not package.get("watch_metrics"):
        lines.append("| n/a | UNKNOWN | THESIS_NO_EVALUABLE_RULES | n/a | n/a |")
    lines += ["", "## Manual review items", ""]
    for item in package.get("manual_review_items") or ["No manual review items emitted by P0.9 rules."]:
        lines.append(f"- {item}")
    lines += ["", "## Limitations", ""]
    for limitation in package.get("limitations") or []:
        lines.append(f"- {limitation}")
    return "\n".join(lines) + FOOTER


def _rule_row(rule: Mapping[str, Any]) -> str:
    return (
        f"| `{rule.get('id')}` | {rule.get('result')} | `{rule.get('reason_code')}` | "
        f"{_fmt(rule.get('current_value'))} | {_fmt(rule.get('threshold'))} |"
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value).replace("|", "\\|")


def _normalize_rules(raw_rules: Any, *, category: str) -> list[dict[str, Any]]:
    if not isinstance(raw_rules, list):
        return []
    rules = []
    for idx, raw in enumerate(raw_rules, start=1):
        if isinstance(raw, str):
            rules.append({"id": f"{category}_{idx}", "description": raw, "source_field": None, "operator": None, "threshold": None, "category": category})
            continue
        if not isinstance(raw, dict):
            continue
        rule = dict(raw)
        rule.setdefault("id", rule.get("name") or f"{category}_{idx}")
        rule.setdefault("category", category)
        if "value" in rule and "threshold" not in rule:
            rule["threshold"] = rule.get("value")
        if "operator" not in rule and "condition" in rule:
            rule["operator"] = rule.get("condition")
        rules.append(rule)
    return rules


def _evaluate_rule(rule: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    source_field = rule.get("source_field") or rule.get("field")
    operator = _normalize_operator(rule.get("operator"))
    threshold = rule.get("threshold")
    base = {
        "id": str(rule.get("id") or "UNKNOWN"),
        "category": rule.get("category") or "UNKNOWN",
        "description": rule.get("description") or rule.get("name") or "",
        "source_field": source_field,
        "operator": operator,
        "threshold": threshold,
        "current_value": None,
        "result": "UNKNOWN",
        "reason_code": "THESIS_RULE_INPUT_MISSING",
        "source_quality": "UNKNOWN",
        "source_class": "operator_curated_thesis_rule",
        "input_lineage": {"source_field": source_field},
    }
    if not source_field or not operator:
        return base
    found, current = _get_path(context, str(source_field))
    base["current_value"] = current
    if not found or current is None:
        return base
    try:
        triggered = _compare(current, operator, threshold)
    except Exception:
        base["reason_code"] = "THESIS_RULE_COMPARISON_FAILED"
        return base
    base["result"] = "TRIGGERED" if triggered else "OK"
    base["reason_code"] = "THESIS_RULE_TRIGGERED" if triggered else "THESIS_RULE_OK"
    return base


def _normalize_operator(op: Any) -> str | None:
    if op is None:
        return None
    val = str(op).strip().lower()
    aliases = {
        ">": "gt", ">=": "gte", "<": "lt", "<=": "lte", "=": "eq", "==": "eq", "!=": "neq",
        "above": "gt", "below": "lt", "at_least": "gte", "at_most": "lte",
        "is": "eq", "not": "neq",
    }
    return aliases.get(val, val)


def _compare(current: Any, operator: str, threshold: Any) -> bool:
    if operator in {"contains", "not_contains"}:
        result = str(threshold) in str(current)
        return result if operator == "contains" else not result
    if operator in {"in", "not_in"}:
        values = threshold if isinstance(threshold, list) else [threshold]
        result = current in values
        return result if operator == "in" else not result
    if operator in {"eq", "neq"}:
        result = str(current).upper() == str(threshold).upper()
        return result if operator == "eq" else not result
    cur = float(current)
    thr = float(threshold)
    if operator == "gt":
        return cur > thr
    if operator == "gte":
        return cur >= thr
    if operator == "lt":
        return cur < thr
    if operator == "lte":
        return cur <= thr
    raise ValueError(f"Unsupported operator: {operator}")


def _build_context(audit_summary: Mapping[str, Any] | None, business_risk: Mapping[str, Any] | None, sensitivity_summary: Mapping[str, Any] | None) -> dict[str, Any]:
    audit = dict(audit_summary or {})
    risk = dict(business_risk or {})
    sensitivity = dict(sensitivity_summary or {})
    return {
        "audit": audit,
        "business_risk": risk,
        "sensitivity": sensitivity,
        # Convenience aliases used by examples/tests.
        "score_raw": audit.get("score_raw"),
        "coverage_pct": audit.get("coverage_pct"),
        "data_confidence": audit.get("data_confidence") or {},
        "model_applicability": audit.get("model_applicability") or {},
        "conclusion_risk": audit.get("conclusion_risk") or {},
        "accounting_quality": risk.get("accounting_quality") or {},
        "capital_allocation": risk.get("capital_allocation") or {},
        "fragility": sensitivity.get("fragility") or {},
    }


def _get_path(obj: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = obj
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _safe_get(obj: Mapping[str, Any] | None, path: str) -> Any:
    if not obj:
        return None
    return _get_path(obj, path)[1]


def _rules_summary(rules: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "total": len(rules),
        "ok": sum(1 for r in rules if r.get("result") == "OK"),
        "triggered": sum(1 for r in rules if r.get("result") == "TRIGGERED"),
        "unknown": sum(1 for r in rules if r.get("result") == "UNKNOWN"),
    }


def _json_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _source_quality(*artifacts: Mapping[str, Any] | None) -> str:
    vals = [str((a or {}).get("source_quality") or "").upper() for a in artifacts if a]
    if any(v in {"LOW", "MEDIUM_LOW"} for v in vals):
        return "MIXED"
    if any(v in {"HIGH", "MEDIUM_HIGH"} for v in vals):
        return "MEDIUM_HIGH"
    return "UNKNOWN"


def _source_class(*artifacts: Mapping[str, Any] | None) -> str:
    vals = sorted({str((a or {}).get("source_class") or "").strip() for a in artifacts if (a or {}).get("source_class")})
    return ",".join(vals) if vals else "operator_curated_research_workflow"


def _unknown_package(ticker: str, reason_code: str, thesis_status: str, watch_metrics: list[Any], invalidation_rules: list[Any], manual_review_items: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "thesis_status.v0.1",
        "sprint": "v4.0-p0.9",
        "status": "UNKNOWN",
        "reason_code": reason_code,
        "ticker": ticker,
        "thesis_status": thesis_status,
        "watch_metrics": watch_metrics,
        "invalidation_rules": invalidation_rules,
        "rules_summary": {"total": 0, "ok": 0, "triggered": 0, "unknown": 0},
        "manual_review_items": manual_review_items,
        "source_quality": "UNKNOWN",
        "source_class": "operator_curated_research_workflow",
        "input_lineage": {"thesis": "missing"},
        "limitations": ["P0.9 cannot evaluate a thesis without machine-readable inputs."],
        "not_investment_advice": True,
    }
