"""P0.12 Run Comparison / Change Detection foundation.

This module compares two already-produced run/audit artifacts and makes changes
explicit: score/coverage, PASS/FAIL/UNKNOWN movements, assumption hash changes,
source/provider changes, and lineage/input changes. It does not fetch live data,
does not recalculate the Snowflake model, and does not mutate canonical v3.1
outputs. UNKNOWN remains visible and is treated as a first-class delta.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from sws_engine.governance.guardrail_tokens import FORBIDDEN_RECOMMENDATION_TOKENS

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

# P1.0: FORBIDDEN_RECOMMENDATION_TOKENS moved to sws_engine.governance.guardrail_tokens

SUMMARY_COMPONENT_PATHS = {
    "data_confidence_level": ("data_confidence", "level"),
    "data_confidence_reason": ("data_confidence", "reason_code"),
    "model_applicability_status": ("model_applicability", "status"),
    "model_applicability_allowed_usage": ("model_applicability", "allowed_score_usage"),
    "model_applicability_reason": ("model_applicability", "reason_code"),
    "conclusion_risk_level": ("conclusion_risk", "risk_level"),
    "conclusion_risk_reason": ("conclusion_risk", "reason_code"),
    "provider_profile": ("provider_profile",),
    "source_quality": ("source_quality",),
    "source_class": ("source_class",),
}


def load_json_artifact(path: str | Path | None, *, required: bool = False) -> dict[str, Any] | None:
    if not path:
        if required:
            raise FileNotFoundError("Required comparison artifact path was not provided")
        return None
    p = Path(path)
    if not p.exists():
        if required:
            raise FileNotFoundError(f"Comparison artifact not found: {p}")
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Comparison artifact must be a JSON object: {p}")
    return data


def build_run_comparison_package(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None,
    *,
    comparison_id: str | None = None,
    artifact_type: str = "audit_summary",
) -> dict[str, Any]:
    """Compare two local artifacts and return a deterministic delta package."""
    prev = dict(previous or {})
    curr = dict(current or {})
    if not prev or not curr:
        return _unknown_comparison(comparison_id=comparison_id, artifact_type=artifact_type)

    ticker = _first_non_empty(curr.get("ticker"), prev.get("ticker"), "UNKNOWN").upper()
    metadata_changes = _metadata_changes(prev, curr)
    score_changes = _score_changes(prev, curr)
    checks_changes = _checks_changes(prev, curr)
    component_changes = _component_changes(prev, curr)
    unknown_changes = _unknown_changes(prev, curr)
    lineage_changes = _lineage_changes(prev, curr)
    warnings_changes = _list_delta(prev.get("warnings"), curr.get("warnings"))

    total_changes = (
        int(metadata_changes["assumptions_hash_changed"])
        + int(metadata_changes["provider_profile_changed"])
        + score_changes["changed_count"]
        + checks_changes["result_changed_count"]
        + component_changes["changed_count"]
        + lineage_changes["changed_count"]
        + warnings_changes["added_count"]
        + warnings_changes["resolved_count"]
        + len(unknown_changes["critical_missing_inputs_added"])
        + len(unknown_changes["critical_missing_inputs_resolved"])
    )
    unknown_preserved = bool(
        unknown_changes["current_unknown_checks_count"]
        or unknown_changes["critical_missing_inputs_added"]
        or unknown_changes["critical_missing_inputs_current"]
        or checks_changes["new_unknown_count"]
    )
    status = "PASS" if total_changes == 0 and not unknown_preserved else "PASS_WITH_LIMITATIONS"
    reason_code = "RUN_COMPARISON_NO_MATERIAL_CHANGE" if total_changes == 0 else "RUN_COMPARISON_CHANGES_DETECTED"
    if unknown_preserved:
        reason_code = "RUN_COMPARISON_UNKNOWN_PRESERVED"

    package = {
        "schema_version": "run_comparison.v0.1",
        "sprint": "v4.0-p0.12",
        "status": status,
        "reason_code": reason_code,
        "comparison_id": comparison_id or _default_comparison_id(prev, curr),
        "artifact_type": artifact_type,
        "ticker": ticker,
        "previous": _artifact_identity(prev),
        "current": _artifact_identity(curr),
        "metadata_changes": metadata_changes,
        "score_changes": score_changes,
        "checks_changes": checks_changes,
        "component_changes": component_changes,
        "unknown_changes": unknown_changes,
        "lineage_changes": lineage_changes,
        "warnings_changes": warnings_changes,
        "material_change_count": total_changes,
        "manual_review_items": _manual_review_items(
            metadata_changes,
            score_changes,
            checks_changes,
            component_changes,
            unknown_changes,
            lineage_changes,
            warnings_changes,
        ),
        "recommendation_language_absent": True,
        "recommendation_guardrail": {"recommendation_language_absent": True, "forbidden_tokens_detected": []},
        "limitations": [
            "P0.12 compares supplied local artifacts only; it does not fetch live data or rerun the engine.",
            "Run comparison is a change-detection artifact, not an investment recommendation and not a buy/sell/hold signal.",
            "Missing sections remain UNKNOWN; they are surfaced rather than inferred.",
            "Field-level lineage comparison is best-effort and depends on lineage objects present in the supplied artifacts.",
        ],
        "not_investment_advice": True,
    }
    return package


def run_comparison_from_files(
    *,
    previous_path: str | Path,
    current_path: str | Path,
    comparison_id: str | None = None,
    artifact_type: str = "audit_summary",
) -> dict[str, Any]:
    return build_run_comparison_package(
        load_json_artifact(previous_path, required=True),
        load_json_artifact(current_path, required=True),
        comparison_id=comparison_id,
        artifact_type=artifact_type,
    )


def run_comparison_to_files(
    output_dir: str | Path,
    *,
    previous_path: str | Path,
    current_path: str | Path,
    comparison_id: str | None = None,
    artifact_type: str = "audit_summary",
) -> dict[str, Any]:
    package = run_comparison_from_files(
        previous_path=previous_path,
        current_path=current_path,
        comparison_id=comparison_id,
        artifact_type=artifact_type,
    )
    return {"package": package, "paths": write_run_comparison_artifacts(package, output_dir)}


def render_run_comparison_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        "# Run Comparison Report",
        "",
        "## Verdict",
        "",
        f"- Status: `{package.get('status')}`",
        f"- Reason code: `{package.get('reason_code')}`",
        f"- Ticker: `{package.get('ticker')}`",
        f"- Comparison ID: `{package.get('comparison_id')}`",
        f"- Material change count: `{package.get('material_change_count')}`",
        "",
        "## Run identity",
        "",
        "| Field | Previous | Current | Changed |",
        "|---|---:|---:|---:|",
    ]
    meta = package.get("metadata_changes") or {}
    for field in ["run_id", "valuation_date", "assumptions_hash", "provider_profile"]:
        prev = (package.get("previous") or {}).get(field)
        curr = (package.get("current") or {}).get(field)
        changed = meta.get(f"{field}_changed") if f"{field}_changed" in meta else prev != curr
        lines.append(f"| `{field}` | `{prev}` | `{curr}` | `{changed}` |")

    lines += ["", "## Score and coverage changes", "", "| Axis | Score previous | Score current | Score delta | Coverage previous | Coverage current | Coverage delta |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in (package.get("score_changes") or {}).get("axes") or []:
        lines.append(
            f"| `{row.get('axis')}` | {row.get('previous_score_raw')} | {row.get('current_score_raw')} | {row.get('score_delta')} | "
            f"{row.get('previous_coverage_pct')} | {row.get('current_coverage_pct')} | {row.get('coverage_delta')} |"
        )
    if not (package.get("score_changes") or {}).get("axes"):
        lines.append("| n/a | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |")

    lines += ["", "## Check-result changes", "", f"- Result changed count: `{(package.get('checks_changes') or {}).get('result_changed_count')}`", f"- New UNKNOWN count: `{(package.get('checks_changes') or {}).get('new_unknown_count')}`", f"- Resolved UNKNOWN count: `{(package.get('checks_changes') or {}).get('resolved_unknown_count')}`", "", "| Check | Previous | Current | Previous reason | Current reason |", "|---|---|---|---|---|"]
    for row in (package.get("checks_changes") or {}).get("changed_checks") or []:
        lines.append(
            f"| `{row.get('check_id')}` | `{row.get('previous_result')}` | `{row.get('current_result')}` | "
            f"`{row.get('previous_reason_code')}` | `{row.get('current_reason_code')}` |"
        )
    if not (package.get("checks_changes") or {}).get("changed_checks"):
        lines.append("| n/a | unchanged/UNKNOWN | unchanged/UNKNOWN | n/a | n/a |")

    lines += ["", "## UNKNOWN and missing-input changes", ""]
    unk = package.get("unknown_changes") or {}
    lines += [
        f"- Previous UNKNOWN checks: `{unk.get('previous_unknown_checks_count')}`",
        f"- Current UNKNOWN checks: `{unk.get('current_unknown_checks_count')}`",
        f"- UNKNOWN delta: `{unk.get('unknown_checks_delta')}`",
        f"- Critical missing inputs added: `{', '.join(unk.get('critical_missing_inputs_added') or []) or 'none'}`",
        f"- Critical missing inputs resolved: `{', '.join(unk.get('critical_missing_inputs_resolved') or []) or 'none'}`",
    ]

    lines += ["", "## Component changes", "", "| Component | Previous | Current | Changed |", "|---|---|---|---|"]
    for row in (package.get("component_changes") or {}).get("components") or []:
        lines.append(f"| `{row.get('component')}` | `{row.get('previous')}` | `{row.get('current')}` | `{row.get('changed')}` |")

    lines += ["", "## Lineage and warning changes", ""]
    lin = package.get("lineage_changes") or {}
    warn = package.get("warnings_changes") or {}
    lines += [
        f"- Lineage changed fields: `{lin.get('changed_count')}`",
        f"- Warnings added: `{', '.join(warn.get('added') or []) or 'none'}`",
        f"- Warnings resolved: `{', '.join(warn.get('resolved') or []) or 'none'}`",
    ]

    lines += ["", "## Manual review items", ""]
    for item in package.get("manual_review_items") or []:
        lines.append(f"- {item}")
    if not package.get("manual_review_items"):
        lines.append("- None generated by P0.12 comparison rules.")

    lines += ["", "## Limitations", ""]
    for limitation in package.get("limitations") or []:
        lines.append(f"- {limitation}")
    text = "\n".join(lines) + FOOTER
    guard = recommendation_guardrail(text)
    if not guard["recommendation_language_absent"]:
        # Keep the markdown writer deterministic and fail-safe if future edits add unsafe text.
        text += "\n<!-- RUN_COMPARISON_RECOMMENDATION_LANGUAGE_REJECTED -->\n"
    return text


def write_run_comparison_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(package.get("ticker") or "UNKNOWN").upper()
    json_path = out / f"{ticker}_run_comparison.json"
    md_path = out / f"{ticker}_run_comparison_report.md"
    md_text = render_run_comparison_report_md(package)
    guard = recommendation_guardrail(md_text)
    package_to_write = dict(package)
    package_to_write["recommendation_language_absent"] = guard["recommendation_language_absent"]
    package_to_write["recommendation_guardrail"] = guard
    if not guard["recommendation_language_absent"]:
        package_to_write["status"] = "FAIL"
        package_to_write["reason_code"] = "RUN_COMPARISON_RECOMMENDATION_LANGUAGE_REJECTED"
    json_path.write_text(json.dumps(package_to_write, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    return {"comparison_json": str(json_path), "comparison_report": str(md_path)}


def recommendation_guardrail(text_or_sections: Any) -> dict[str, Any]:
    text = json.dumps(text_or_sections, sort_keys=True) if not isinstance(text_or_sections, str) else text_or_sections
    padded = f" {text} "
    detected = [token.strip() for token in FORBIDDEN_RECOMMENDATION_TOKENS if token in padded]
    return {
        "recommendation_language_absent": not detected,
        "forbidden_tokens_detected": detected,
        "reason_code": "RUN_COMPARISON_NO_RECOMMENDATION_LANGUAGE" if not detected else "RUN_COMPARISON_RECOMMENDATION_LANGUAGE_REJECTED",
    }


def _unknown_comparison(*, comparison_id: str | None, artifact_type: str) -> dict[str, Any]:
    return {
        "schema_version": "run_comparison.v0.1",
        "sprint": "v4.0-p0.12",
        "status": "UNKNOWN",
        "reason_code": "RUN_COMPARISON_INPUTS_MISSING",
        "comparison_id": comparison_id or "UNKNOWN",
        "artifact_type": artifact_type,
        "ticker": "UNKNOWN",
        "previous": {},
        "current": {},
        "metadata_changes": {},
        "score_changes": {"axes": [], "changed_count": 0},
        "checks_changes": {"changed_checks": [], "result_changed_count": 0, "new_unknown_count": 0, "resolved_unknown_count": 0},
        "component_changes": {"components": [], "changed_count": 0},
        "unknown_changes": {
            "previous_unknown_checks_count": None,
            "current_unknown_checks_count": None,
            "unknown_checks_delta": None,
            "critical_missing_inputs_previous": [],
            "critical_missing_inputs_current": [],
            "critical_missing_inputs_added": [],
            "critical_missing_inputs_resolved": [],
        },
        "lineage_changes": {"changed_fields": [], "changed_count": 0},
        "warnings_changes": {"added": [], "resolved": [], "unchanged": [], "added_count": 0, "resolved_count": 0},
        "material_change_count": 0,
        "manual_review_items": ["Previous and/or current artifact missing; comparison is UNKNOWN."],
        "recommendation_language_absent": True,
        "recommendation_guardrail": {"recommendation_language_absent": True, "forbidden_tokens_detected": []},
        "limitations": ["P0.12 requires two local JSON artifacts."],
        "not_investment_advice": True,
    }


def _metadata_changes(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> dict[str, Any]:
    fields = ["run_id", "valuation_date", "assumptions_hash", "provider_profile", "engine_version"]
    out: dict[str, Any] = {}
    for field in fields:
        out[f"{field}_changed"] = _norm(prev.get(field)) != _norm(curr.get(field))
    out["assumptions_hash_previous"] = prev.get("assumptions_hash") or "UNKNOWN"
    out["assumptions_hash_current"] = curr.get("assumptions_hash") or "UNKNOWN"
    out["assumptions_hash_changed"] = out["assumptions_hash_changed"]
    out["provider_profile_previous"] = prev.get("provider_profile") or "UNKNOWN"
    out["provider_profile_current"] = curr.get("provider_profile") or "UNKNOWN"
    out["provider_profile_changed"] = out["provider_profile_changed"]
    return out


def _artifact_identity(obj: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ticker": str(obj.get("ticker") or "UNKNOWN").upper(),
        "exchange": obj.get("exchange") or "UNKNOWN",
        "run_id": obj.get("run_id") or "UNKNOWN",
        "valuation_date": obj.get("valuation_date") or "UNKNOWN",
        "assumptions_hash": obj.get("assumptions_hash") or "UNKNOWN",
        "provider_profile": obj.get("provider_profile") or "UNKNOWN",
        "source_quality": obj.get("source_quality") or "UNKNOWN",
        "source_class": obj.get("source_class") or "UNKNOWN",
    }


def _score_changes(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> dict[str, Any]:
    p_scores = _score_summary(prev)
    c_scores = _score_summary(curr)
    axes = sorted(set(p_scores) | set(c_scores))
    rows = []
    changed_count = 0
    for axis in axes:
        p = p_scores.get(axis) or {}
        c = c_scores.get(axis) or {}
        p_score = _num_or_none(p.get("score_raw"))
        c_score = _num_or_none(c.get("score_raw"))
        p_cov = _num_or_none(p.get("coverage_pct"))
        c_cov = _num_or_none(c.get("coverage_pct"))
        row = {
            "axis": axis,
            "previous_score_raw": p_score if p_score is not None else "UNKNOWN",
            "current_score_raw": c_score if c_score is not None else "UNKNOWN",
            "score_delta": _delta(c_score, p_score),
            "previous_coverage_pct": p_cov if p_cov is not None else "UNKNOWN",
            "current_coverage_pct": c_cov if c_cov is not None else "UNKNOWN",
            "coverage_delta": _delta(c_cov, p_cov),
        }
        row["changed"] = row["score_delta"] not in (0, None, "UNKNOWN") or row["coverage_delta"] not in (0, None, "UNKNOWN")
        changed_count += int(bool(row["changed"]))
        rows.append(row)
    return {"axes": rows, "changed_count": changed_count}


def _score_summary(obj: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(obj.get("score_summary"), dict):
        return dict(obj.get("score_summary") or {})
    snow = obj.get("snowflake") or {}
    if isinstance(snow.get("axis_scores"), dict):
        return dict(snow.get("axis_scores") or {})
    if isinstance(obj.get("axis_scores"), dict):
        return dict(obj.get("axis_scores") or {})
    return {}


def _checks_changes(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> dict[str, Any]:
    p_checks = _check_map(prev)
    c_checks = _check_map(curr)
    changed = []
    new_unknown = 0
    resolved_unknown = 0
    reason_changed = 0
    for cid in sorted(set(p_checks) | set(c_checks)):
        p = p_checks.get(cid) or {}
        c = c_checks.get(cid) or {}
        pr = _result_value(p)
        cr = _result_value(c)
        prc = p.get("reason_code") or "UNKNOWN"
        crc = c.get("reason_code") or "UNKNOWN"
        if pr != cr or prc != crc:
            changed.append({
                "check_id": cid,
                "previous_result": pr,
                "current_result": cr,
                "previous_reason_code": prc,
                "current_reason_code": crc,
            })
        new_unknown += int(pr != "UNKNOWN" and cr == "UNKNOWN")
        resolved_unknown += int(pr == "UNKNOWN" and cr != "UNKNOWN")
        reason_changed += int(prc != crc)
    return {
        "changed_checks": changed,
        "result_changed_count": sum(1 for row in changed if row["previous_result"] != row["current_result"]),
        "reason_code_changed_count": reason_changed,
        "new_unknown_count": new_unknown,
        "resolved_unknown_count": resolved_unknown,
        "previous_checks_count": len(p_checks),
        "current_checks_count": len(c_checks),
        "reason_code": "RUN_COMPARISON_CHECKS_CHANGED" if changed else "RUN_COMPARISON_CHECKS_UNCHANGED_OR_UNAVAILABLE",
    }


def _check_map(obj: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    checks = obj.get("checks")
    if checks is None and isinstance(obj.get("output"), dict):
        checks = obj["output"].get("checks")
    if not isinstance(checks, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for i, chk in enumerate(checks):
        if not isinstance(chk, dict):
            continue
        cid = str(chk.get("id") or chk.get("check_id") or chk.get("name") or f"check_{i}")
        result[cid] = dict(chk)
    return result


def _component_changes(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for name, path in SUMMARY_COMPONENT_PATHS.items():
        p = _get_path(prev, path)
        c = _get_path(curr, path)
        changed = _norm(p) != _norm(c)
        rows.append({"component": name, "previous": p if p is not None else "UNKNOWN", "current": c if c is not None else "UNKNOWN", "changed": changed})
    return {"components": rows, "changed_count": sum(1 for row in rows if row["changed"])}


def _unknown_changes(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> dict[str, Any]:
    p_unknown = _unknown_count(prev)
    c_unknown = _unknown_count(curr)
    p_missing = _string_set(prev.get("critical_missing_inputs")) | _string_set(_get_path(prev, ("data_confidence", "critical_missing_inputs")))
    c_missing = _string_set(curr.get("critical_missing_inputs")) | _string_set(_get_path(curr, ("data_confidence", "critical_missing_inputs")))
    return {
        "previous_unknown_checks_count": p_unknown,
        "current_unknown_checks_count": c_unknown,
        "unknown_checks_delta": _delta(c_unknown, p_unknown),
        "critical_missing_inputs_previous": sorted(p_missing),
        "critical_missing_inputs_current": sorted(c_missing),
        "critical_missing_inputs_added": sorted(c_missing - p_missing),
        "critical_missing_inputs_resolved": sorted(p_missing - c_missing),
        "reason_code": "RUN_COMPARISON_UNKNOWN_PRESERVED" if c_unknown or c_missing else "RUN_COMPARISON_NO_UNKNOWN_DETECTED",
    }


def _unknown_count(obj: Mapping[str, Any]) -> int | None:
    candidates = [
        _get_path(obj, ("checks_summary", "UNKNOWN")),
        _get_path(obj, ("data_confidence", "unknown_checks_count")),
        obj.get("unknown_checks_count"),
    ]
    for cand in candidates:
        n = _num_or_none(cand)
        if n is not None:
            return int(n)
    checks = _check_map(obj)
    if checks:
        return sum(1 for chk in checks.values() if _result_value(chk) == "UNKNOWN")
    return None


def _lineage_changes(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> dict[str, Any]:
    p_lin = _lineage_map(prev)
    c_lin = _lineage_map(curr)
    changed = []
    for field in sorted(set(p_lin) | set(c_lin)):
        p = p_lin.get(field)
        c = c_lin.get(field)
        if _stable(p) != _stable(c):
            changed.append({"field": field, "previous": p if p is not None else "UNKNOWN", "current": c if c is not None else "UNKNOWN"})
    return {"changed_fields": changed, "changed_count": len(changed), "reason_code": "RUN_COMPARISON_LINEAGE_CHANGED" if changed else "RUN_COMPARISON_LINEAGE_UNCHANGED_OR_UNAVAILABLE"}


def _lineage_map(obj: Mapping[str, Any]) -> dict[str, Any]:
    candidates = []
    if isinstance(obj.get("input_lineage"), dict):
        candidates.append(obj["input_lineage"])
    if isinstance(obj.get("lineage"), dict):
        candidates.append(obj["lineage"])
        if isinstance(obj["lineage"].get("field_lineage"), dict):
            candidates.append(obj["lineage"]["field_lineage"])
    if isinstance(obj.get("field_lineage"), dict):
        candidates.append(obj["field_lineage"])
    merged: dict[str, Any] = {}
    for candidate in candidates:
        for key, value in candidate.items():
            if isinstance(value, (dict, str, int, float, bool)) or value is None:
                merged[str(key)] = value
    return merged


def _list_delta(prev: Any, curr: Any) -> dict[str, Any]:
    p = _string_set(prev)
    c = _string_set(curr)
    return {
        "previous": sorted(p),
        "current": sorted(c),
        "added": sorted(c - p),
        "resolved": sorted(p - c),
        "unchanged": sorted(p & c),
        "added_count": len(c - p),
        "resolved_count": len(p - c),
    }


def _manual_review_items(*parts: Mapping[str, Any]) -> list[str]:
    meta, scores, checks, components, unknowns, lineage, warnings = parts
    items: list[str] = []
    if meta.get("assumptions_hash_changed"):
        items.append("Assumptions hash changed; review whether score/valuation deltas are input-driven or assumption-driven.")
    if meta.get("provider_profile_changed"):
        items.append("Provider profile changed; verify provider degradation and source-quality comparability.")
    if scores.get("changed_count"):
        items.append(f"{scores.get('changed_count')} score/coverage axes changed; review axis-level deltas.")
    if checks.get("result_changed_count"):
        items.append(f"{checks.get('result_changed_count')} check results changed; review PASS/FAIL/UNKNOWN movements.")
    if checks.get("new_unknown_count"):
        items.append(f"{checks.get('new_unknown_count')} checks became UNKNOWN; do not compare scores without reviewing missing inputs.")
    if unknowns.get("critical_missing_inputs_added"):
        items.append("New critical missing inputs appeared: " + ", ".join(unknowns.get("critical_missing_inputs_added") or []))
    if components.get("changed_count"):
        items.append(f"{components.get('changed_count')} audit components changed; review data confidence, applicability and conclusion risk.")
    if lineage.get("changed_count"):
        items.append(f"{lineage.get('changed_count')} lineage fields changed; verify source precedence and staleness.")
    if warnings.get("added"):
        items.append("New warnings appeared: " + ", ".join(warnings.get("added") or []))
    if not items:
        items.append("No material P0.12 change drivers detected; still review source dates before relying on the comparison.")
    return items


def _default_comparison_id(prev: Mapping[str, Any], curr: Mapping[str, Any]) -> str:
    ticker = _first_non_empty(curr.get("ticker"), prev.get("ticker"), "UNKNOWN").upper()
    return f"{ticker}:{prev.get('run_id') or prev.get('valuation_date') or 'previous'}->{curr.get('run_id') or curr.get('valuation_date') or 'current'}"


def _get_path(obj: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = obj
    for part in path:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
    return cur


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return "UNKNOWN"


def _num_or_none(value: Any) -> float | None:
    if value is None or value == "UNKNOWN":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _delta(current: float | int | None, previous: float | int | None) -> float | str:
    if current is None or previous is None:
        return "UNKNOWN"
    val = float(current) - float(previous)
    return round(val, 6)


def _result_value(chk: Mapping[str, Any]) -> str:
    return str(chk.get("result") or chk.get("status") or "UNKNOWN").upper()


def _norm(value: Any) -> Any:
    if value in (None, ""):
        return "UNKNOWN"
    if isinstance(value, str):
        return value.strip()
    return value


def _stable(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, Mapping):
        return {str(k) for k in value.keys()}
    if isinstance(value, (list, tuple, set)):
        return {str(x) for x in value if str(x)}
    return {str(value)}
