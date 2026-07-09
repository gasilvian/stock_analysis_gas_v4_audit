"""P0.8 Watchlist Audit foundation.

This module triages a local watchlist using already-produced audit artifacts.
It does not fetch data, does not calculate buy/sell/hold signals, and does not
mutate the canonical v3.1 output schema. Missing artifacts remain UNKNOWN and
are surfaced as manual review items.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

BUCKET_RESEARCHABLE_NOW = "Researchable Now"
BUCKET_DATA_LIMITED = "Data Limited"
BUCKET_NEEDS_DIFFERENT_MODEL = "Needs Different Model"
BUCKET_IGNORE_FOR_NOW = "Ignore for Now"
BUCKET_MANUAL_REVIEW_REQUIRED = "Manual Review Required"

BUCKETS = [
    BUCKET_RESEARCHABLE_NOW,
    BUCKET_DATA_LIMITED,
    BUCKET_NEEDS_DIFFERENT_MODEL,
    BUCKET_IGNORE_FOR_NOW,
    BUCKET_MANUAL_REVIEW_REQUIRED,
]

PRIORITY_WEIGHT = {"critical": 5, "very_high": 5, "high": 4, "medium": 3, "low": 2, "watch": 2, "ignore": 1, "": 1}
CONFIDENCE_WEIGHT = {"HIGH": 4, "MEDIUM": 3, "LOW": 1, "UNKNOWN": 0}
RISK_WEIGHT = {"LOW": 3, "MEDIUM": 2, "HIGH": 0, "UNKNOWN": 0}


def load_watchlist_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load a local watchlist CSV.

    Required column: ticker. Optional columns: exchange, idea_source, priority,
    notes. Unknown columns are preserved under metadata.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Watchlist CSV not found: {p}")
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    loaded: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        ticker = str(row.get("ticker") or row.get("Ticker") or "").strip().upper()
        if not ticker:
            loaded.append({
                "row_number": idx,
                "ticker": "UNKNOWN",
                "status": "UNKNOWN",
                "reason_code": "WATCHLIST_TICKER_MISSING",
                "idea_source": row.get("idea_source") or row.get("source") or "UNKNOWN",
                "priority": row.get("priority") or "",
                "metadata": {k: v for k, v in row.items() if k},
            })
            continue
        loaded.append({
            "row_number": idx,
            "ticker": ticker,
            "exchange": str(row.get("exchange") or row.get("Exchange") or "").strip() or None,
            "idea_source": str(row.get("idea_source") or row.get("source") or row.get("idea") or "manual").strip() or "manual",
            "priority": str(row.get("priority") or "medium").strip().lower() or "medium",
            "notes": str(row.get("notes") or row.get("comment") or "").strip(),
            "metadata": {k: v for k, v in row.items() if k not in {"ticker", "Ticker", "exchange", "Exchange", "idea_source", "source", "idea", "priority", "notes", "comment"}},
        })
    return loaded


def audit_watchlist(
    watchlist_rows: Sequence[Mapping[str, Any]],
    *,
    audit_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    business_risks: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a deterministic watchlist triage package.

    The input artifacts are expected to be outputs from previous P0.x modules.
    If an audit summary is missing for a ticker, the ticker is not dropped; it is
    classified as Data Limited with UNKNOWN artifact status.
    """
    summaries = {str(k).upper(): dict(v) for k, v in (audit_summaries or {}).items()}
    risks = {str(k).upper(): dict(v) for k, v in (business_risks or {}).items()}
    items = []
    for row in watchlist_rows:
        item = _triage_row(row, summaries.get(str(row.get("ticker", "UNKNOWN")).upper()), risks.get(str(row.get("ticker", "UNKNOWN")).upper()))
        items.append(item)
    bucket_counts = {bucket: sum(1 for item in items if item.get("bucket") == bucket) for bucket in BUCKETS}
    manual_review_count = sum(1 for item in items if item.get("manual_review_required"))
    unknown_artifact_count = sum(1 for item in items if item.get("artifact_status") == "UNKNOWN")
    status = "PASS_WITH_LIMITATIONS"
    reason_code = "WATCHLIST_AUDIT_COMPUTED"
    if not items:
        status = "UNKNOWN"
        reason_code = "WATCHLIST_INPUTS_MISSING"
    elif unknown_artifact_count == len(items):
        status = "UNKNOWN"
        reason_code = "WATCHLIST_AUDIT_ARTIFACTS_MISSING"
    return {
        "schema_version": "watchlist_audit.v0.1",
        "sprint": "v4.0-p0.8",
        "status": status,
        "reason_code": reason_code,
        "watchlist_size": len(items),
        "bucket_counts": bucket_counts,
        "manual_review_count": manual_review_count,
        "unknown_artifact_count": unknown_artifact_count,
        "research_queue": _research_queue(items),
        "items": items,
        "source_quality": _aggregate_item_value(items, "source_quality"),
        "source_class": _aggregate_item_value(items, "source_class"),
        "limitations": [
            "P0.8 uses existing audit/business-risk artifacts only; no live data is fetched.",
            "Bucket assignment is process triage, not investment advice and not a buy/sell/hold signal.",
            "Missing audit artifacts remain UNKNOWN and are surfaced rather than inferred.",
        ],
        "not_investment_advice": True,
    }


def audit_watchlist_from_files(
    watchlist_csv: str | Path,
    *,
    audit_dir: str | Path | None = None,
    business_risk_dir: str | Path | None = None,
) -> dict[str, Any]:
    rows = load_watchlist_csv(watchlist_csv)
    summaries = load_artifact_map(audit_dir, artifact_kind="audit") if audit_dir else {}
    risks = load_artifact_map(business_risk_dir, artifact_kind="business_risk") if business_risk_dir else {}
    return audit_watchlist(rows, audit_summaries=summaries, business_risks=risks)


def audit_watchlist_to_files(
    watchlist_csv: str | Path,
    output_dir: str | Path,
    *,
    audit_dir: str | Path | None = None,
    business_risk_dir: str | Path | None = None,
) -> dict[str, Any]:
    package = audit_watchlist_from_files(watchlist_csv, audit_dir=audit_dir, business_risk_dir=business_risk_dir)
    return {"package": package, "paths": write_watchlist_artifacts(package, output_dir)}


def load_artifact_map(path: str | Path | None, *, artifact_kind: str = "audit") -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    base = Path(path)
    if not base.exists():
        raise FileNotFoundError(f"Artifact directory not found: {base}")
    patterns = ["*.json", "*/*.json"]
    artifacts: dict[str, dict[str, Any]] = {}
    for pattern in patterns:
        for p in base.glob(pattern):
            if p.is_dir():
                continue
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if artifact_kind == "audit" and not _looks_like_audit_summary(obj):
                continue
            if artifact_kind == "business_risk" and not _looks_like_business_risk(obj):
                continue
            ticker = str(obj.get("ticker") or "").upper()
            if ticker:
                # Later files win; this mirrors latest artifact semantics and keeps
                # tests deterministic because paths are sorted by glob order per FS.
                artifacts[ticker] = obj
    return artifacts


def render_watchlist_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        "# Watchlist Audit Report",
        "",
        "## Verdict",
        "",
        f"- Status: `{package.get('status', 'UNKNOWN')}`",
        f"- Reason code: `{package.get('reason_code', 'UNKNOWN')}`",
        f"- Watchlist size: `{package.get('watchlist_size', 0)}`",
        f"- Manual review count: `{package.get('manual_review_count', 0)}`",
        f"- Unknown artifact count: `{package.get('unknown_artifact_count', 0)}`",
        "",
        "## Bucket counts",
        "",
        "| Bucket | Count |",
        "|---|---:|",
    ]
    for bucket in BUCKETS:
        lines.append(f"| {bucket} | {(package.get('bucket_counts') or {}).get(bucket, 0)} |")
    lines += [
        "",
        "## Research queue",
        "",
        "| Rank | Ticker | Bucket | Priority | Score | Data confidence | Applicability | Conclusion risk |",
        "|---:|---|---|---|---:|---|---|---|",
    ]
    queue = package.get("research_queue") or []
    if queue:
        for row in queue:
            lines.append(
                f"| {row.get('rank')} | `{row.get('ticker')}` | {row.get('bucket')} | "
                f"{row.get('priority')} | {row.get('research_queue_score')} | "
                f"{row.get('data_confidence_level')} | {row.get('model_applicability_status')} | {row.get('conclusion_risk_level')} |"
            )
    else:
        lines.append("| n/a | n/a | n/a | n/a | 0 | UNKNOWN | UNKNOWN | UNKNOWN |")
    lines += [
        "",
        "## Full triage",
        "",
        "| Ticker | Bucket | Manual review | Reason codes | Manual review items |",
        "|---|---|---|---|---|",
    ]
    for item in package.get("items") or []:
        reasons = ", ".join(f"`{r}`" for r in item.get("reason_codes", [])) or "`UNKNOWN`"
        review = "<br>".join(str(x) for x in item.get("manual_review_items", [])) or "n/a"
        lines.append(
            f"| `{item.get('ticker')}` | {item.get('bucket')} | {item.get('manual_review_required')} | {reasons} | {review} |"
        )
    lines += ["", "## Limitations", ""]
    for limitation in package.get("limitations") or []:
        lines.append(f"- {limitation}")
    return "\n".join(lines) + FOOTER


def write_watchlist_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "watchlist_audit.json"
    md_path = out / "watchlist_audit_report.md"
    json_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_watchlist_report_md(package), encoding="utf-8")
    return {"watchlist_audit_json": str(json_path), "watchlist_audit_report_md": str(md_path)}


def _triage_row(row: Mapping[str, Any], audit_summary: Mapping[str, Any] | None, business_risk: Mapping[str, Any] | None) -> dict[str, Any]:
    ticker = str(row.get("ticker") or "UNKNOWN").upper()
    priority = str(row.get("priority") or "medium").lower()
    if ticker == "UNKNOWN" or not audit_summary:
        return _unknown_item(row, reason="WATCHLIST_AUDIT_ARTIFACT_MISSING")
    dc = dict(audit_summary.get("data_confidence") or {})
    ma = dict(audit_summary.get("model_applicability") or {})
    cr = dict(audit_summary.get("conclusion_risk") or {})
    br = dict(business_risk or {})
    reason_codes: list[str] = []
    review_items: list[str] = []
    bucket = BUCKET_RESEARCHABLE_NOW

    ma_status = str(ma.get("status") or "UNKNOWN")
    allowed_usage = str(ma.get("allowed_score_usage") or "UNKNOWN")
    company_type = str(ma.get("company_type_detected") or "unknown")
    if ma_status == "NOT_APPLICABLE" or allowed_usage == "do_not_compare" and company_type in {"fund_etf_excluded", "fund", "etf"}:
        bucket = BUCKET_IGNORE_FOR_NOW
        reason_codes.append("WATCHLIST_NOT_APPLICABLE_IGNORED")
        review_items.append("This item is not a company-analysis target under the current model; keep it out of ranked equity research.")
    elif ma_status == "DEGRADED" or allowed_usage in {"audit_only", "do_not_compare"}:
        bucket = BUCKET_NEEDS_DIFFERENT_MODEL
        reason_codes.append("WATCHLIST_NEEDS_DIFFERENT_MODEL")
        review_items.append("Use a sector/model-specific workflow or manual review before comparing this ticker.")
    elif ma_status == "UNKNOWN":
        bucket = BUCKET_DATA_LIMITED
        reason_codes.append("WATCHLIST_MODEL_APPLICABILITY_UNKNOWN")
        review_items.append("Resolve model applicability before using this ticker in watchlist ranking.")

    dc_level = str(dc.get("level") or "UNKNOWN")
    unknown_checks_count = int(dc.get("unknown_checks_count") or 0)
    critical_missing = list(dc.get("critical_missing_inputs") or audit_summary.get("critical_missing_inputs") or [])
    if dc_level in {"LOW", "UNKNOWN"} or unknown_checks_count >= 10 or critical_missing:
        if bucket == BUCKET_RESEARCHABLE_NOW:
            bucket = BUCKET_DATA_LIMITED
        reason_codes.append("WATCHLIST_DATA_LIMITED")
        review_items.append("Review UNKNOWN checks, critical missing inputs and source quality before deep research.")

    risk_level = str(cr.get("risk_level") or "UNKNOWN")
    if risk_level in {"HIGH", "UNKNOWN"}:
        if bucket == BUCKET_RESEARCHABLE_NOW:
            bucket = BUCKET_MANUAL_REVIEW_REQUIRED
        reason_codes.append("WATCHLIST_CONCLUSION_RISK_REVIEW_REQUIRED")
        review_items.append("Conclusion risk is high or unknown; manual review is required before relying on this analysis.")

    red_summary = br.get("red_flags_summary") or {}
    red_fail_count = int(red_summary.get("fail_count") or 0)
    high_red_count = int(red_summary.get("high_severity_fail_count") or 0)
    if red_fail_count:
        if bucket == BUCKET_RESEARCHABLE_NOW:
            bucket = BUCKET_MANUAL_REVIEW_REQUIRED
        reason_codes.append("WATCHLIST_RED_FLAGS_REVIEW_REQUIRED")
        review_items.append(f"Business-risk module reports {red_fail_count} red flag(s), including {high_red_count} high-severity flag(s).")

    provider_degraded = bool(audit_summary.get("provider_degradation_visible"))
    if provider_degraded:
        reason_codes.append("WATCHLIST_PROVIDER_DEGRADED")
        review_items.append("Provider degradation is visible; verify material fields against official or curated sources.")

    if not reason_codes:
        reason_codes.append("WATCHLIST_RESEARCHABLE_NOW")
    queue_score = _research_score(row, dc_level, risk_level, ma_status, bucket, red_fail_count)
    return {
        "ticker": ticker,
        "exchange": row.get("exchange") or audit_summary.get("exchange"),
        "idea_source": row.get("idea_source") or "manual",
        "priority": priority,
        "notes": row.get("notes") or "",
        "bucket": bucket,
        "artifact_status": "PASS",
        "reason_codes": sorted(set(reason_codes)),
        "manual_review_required": bucket in {BUCKET_DATA_LIMITED, BUCKET_NEEDS_DIFFERENT_MODEL, BUCKET_MANUAL_REVIEW_REQUIRED} or bool(review_items),
        "manual_review_items": sorted(set(review_items)),
        "research_queue_score": queue_score,
        "data_confidence_level": dc_level,
        "data_confidence_grade": dc.get("confidence_grade"),
        "model_applicability_status": ma_status,
        "allowed_score_usage": allowed_usage,
        "company_type_detected": company_type,
        "conclusion_risk_level": risk_level,
        "red_flags_count": red_fail_count,
        "unknown_checks_count": unknown_checks_count,
        "source_quality": _source_quality_from_artifacts(audit_summary, business_risk),
        "source_class": _source_class_from_artifacts(audit_summary, business_risk),
        "input_lineage": {
            "audit_summary_run_id": audit_summary.get("run_id"),
            "audit_schema_version": audit_summary.get("schema_version"),
            "business_risk_schema_version": br.get("schema_version") if br else None,
            "watchlist_row_number": row.get("row_number"),
        },
    }


def _unknown_item(row: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    ticker = str(row.get("ticker") or "UNKNOWN").upper()
    review = "Run audit-company for this ticker and provide the resulting audit summary before triage."
    if ticker == "UNKNOWN":
        review = "Populate ticker in the watchlist row."
        reason = "WATCHLIST_TICKER_MISSING"
    return {
        "ticker": ticker,
        "exchange": row.get("exchange"),
        "idea_source": row.get("idea_source") or "manual",
        "priority": row.get("priority") or "medium",
        "notes": row.get("notes") or "",
        "bucket": BUCKET_DATA_LIMITED,
        "artifact_status": "UNKNOWN",
        "reason_codes": [reason],
        "manual_review_required": True,
        "manual_review_items": [review],
        "research_queue_score": 0,
        "data_confidence_level": "UNKNOWN",
        "data_confidence_grade": "UNKNOWN",
        "model_applicability_status": "UNKNOWN",
        "allowed_score_usage": "audit_only",
        "company_type_detected": "unknown",
        "conclusion_risk_level": "UNKNOWN",
        "red_flags_count": None,
        "unknown_checks_count": None,
        "source_quality": "missing",
        "source_class": "E0/E3",
        "input_lineage": {"watchlist_row_number": row.get("row_number"), "audit_summary": None},
    }


def _research_score(row: Mapping[str, Any], data_confidence: str, conclusion_risk: str, model_status: str, bucket: str, red_flags_count: int) -> int:
    if bucket in {BUCKET_IGNORE_FOR_NOW, BUCKET_NEEDS_DIFFERENT_MODEL}:
        return 0
    priority = PRIORITY_WEIGHT.get(str(row.get("priority") or "").lower(), 2)
    score = priority * 10 + CONFIDENCE_WEIGHT.get(data_confidence, 0) * 5 + RISK_WEIGHT.get(conclusion_risk, 0) * 4
    if model_status != "STANDARD_OK":
        score -= 10
    score -= min(red_flags_count, 5) * 3
    if bucket == BUCKET_MANUAL_REVIEW_REQUIRED:
        score -= 8
    if bucket == BUCKET_DATA_LIMITED:
        score -= 15
    return max(int(score), 0)


def _research_queue(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    eligible = [i for i in items if i.get("bucket") in {BUCKET_RESEARCHABLE_NOW, BUCKET_MANUAL_REVIEW_REQUIRED, BUCKET_DATA_LIMITED}]
    ranked = sorted(eligible, key=lambda x: (-int(x.get("research_queue_score") or 0), str(x.get("ticker") or "")))
    return [
        {
            "rank": idx,
            "ticker": item.get("ticker"),
            "bucket": item.get("bucket"),
            "priority": item.get("priority"),
            "research_queue_score": item.get("research_queue_score"),
            "data_confidence_level": item.get("data_confidence_level"),
            "model_applicability_status": item.get("model_applicability_status"),
            "conclusion_risk_level": item.get("conclusion_risk_level"),
            "manual_review_required": item.get("manual_review_required"),
        }
        for idx, item in enumerate(ranked, start=1)
    ]


def _looks_like_audit_summary(obj: Mapping[str, Any]) -> bool:
    return str(obj.get("schema_version", "")).startswith("audit_summary") or "data_confidence" in obj and "model_applicability" in obj


def _looks_like_business_risk(obj: Mapping[str, Any]) -> bool:
    return str(obj.get("schema_version", "")).startswith("business_risk_package") or "red_flags_summary" in obj


def _source_quality_from_artifacts(audit_summary: Mapping[str, Any], business_risk: Mapping[str, Any] | None) -> str:
    dc = audit_summary.get("data_confidence") or {}
    if business_risk and business_risk.get("source_quality") == "missing":
        return "missing"
    if audit_summary.get("provider_degradation_visible"):
        return "approximation"
    return str(dc.get("source_quality") or dc.get("source_quality_score") or "approximation")


def _source_class_from_artifacts(audit_summary: Mapping[str, Any], business_risk: Mapping[str, Any] | None) -> str:
    if business_risk and business_risk.get("source_class"):
        return str(business_risk.get("source_class"))
    dc = audit_summary.get("data_confidence") or {}
    mix = dc.get("source_class_mix") or {}
    if mix:
        return ",".join(sorted(mix.keys()))
    return "E3"


def _aggregate_item_value(items: Sequence[Mapping[str, Any]], key: str) -> str:
    values = [str(i.get(key)) for i in items if i.get(key)]
    if not values:
        return "missing"
    if "missing" in values:
        return "missing"
    if any("E0" in v for v in values) and key == "source_class":
        return "E0/E3"
    return sorted(set(values))[0]
