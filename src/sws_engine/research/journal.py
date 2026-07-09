"""P0.9 Decision Journal foundation.

The journal records research-process decisions only. It does not record broker
orders, does not produce buy/sell/hold language, and keeps data confidence and
thesis status visible at the point of decision.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import yaml

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

ALLOWED_DECISION_TYPES = {
    "research_deeper",
    "pass",
    "add_watch",
    "remove_watch",
    "review_thesis",
    "personal_action_external",
}
FORBIDDEN_DECISION_TYPES = {"buy", "sell", "hold", "strong_buy", "strong_sell"}


def load_decision(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Decision file not found: {p}")
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Decision input must parse to a mapping")
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


def build_decision_record(
    decision: Mapping[str, Any] | None,
    *,
    audit_summary: Mapping[str, Any] | None = None,
    thesis_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision_obj = dict(decision or {})
    ticker = str(decision_obj.get("ticker") or (audit_summary or {}).get("ticker") or (thesis_status or {}).get("ticker") or "UNKNOWN").upper()
    decision_type = str(decision_obj.get("decision_type") or "").strip().lower()
    if not decision_obj or not ticker or ticker == "UNKNOWN":
        return _unknown_record(ticker, "DECISION_INPUTS_MISSING", "Decision input must include a ticker and decision_type.")
    if decision_type in FORBIDDEN_DECISION_TYPES:
        return _unknown_record(ticker, "DECISION_TYPE_NOT_ALLOWED", f"decision_type `{decision_type}` is not allowed in this product scope.")
    if decision_type not in ALLOWED_DECISION_TYPES:
        return _unknown_record(ticker, "DECISION_TYPE_NOT_ALLOWED", f"decision_type `{decision_type}` is not allowed.")

    audit = dict(audit_summary or {})
    thesis = dict(thesis_status or {})
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    record = {
        "schema_version": "decision_journal.v0.1",
        "sprint": "v4.0-p0.9",
        "status": "PASS",
        "reason_code": "DECISION_RECORDED",
        "decision_id": decision_obj.get("decision_id") or f"dec_{uuid4().hex[:12]}",
        "created_at": decision_obj.get("created_at") or now,
        "date": _json_scalar(decision_obj.get("date") or date.today().isoformat()),
        "ticker": ticker,
        "decision_type": decision_type,
        "thesis_snapshot_ref": decision_obj.get("thesis_snapshot_ref") or thesis.get("schema_version"),
        "expected_outcome": decision_obj.get("expected_outcome") or "",
        "review_date": _json_scalar(decision_obj.get("review_date")),
        "notes": decision_obj.get("notes") or "",
        "run_id_at_decision": decision_obj.get("run_id_at_decision") or audit.get("run_id"),
        "data_confidence_at_decision": _safe_path(audit, "data_confidence.level") or audit.get("data_confidence_level") or "UNKNOWN",
        "model_applicability_at_decision": _safe_path(audit, "model_applicability.status") or "UNKNOWN",
        "conclusion_risk_at_decision": _safe_path(audit, "conclusion_risk.risk_level") or "UNKNOWN",
        "thesis_status_at_decision": thesis.get("thesis_status") or "UNKNOWN",
        "manual_review_items_at_decision": list((audit.get("manual_review_items") or []) + (thesis.get("manual_review_items") or [])),
        "post_mortem": decision_obj.get("post_mortem") or {},
        "source_quality": audit.get("source_quality") or thesis.get("source_quality") or "UNKNOWN",
        "source_class": audit.get("source_class") or thesis.get("source_class") or "operator_curated_research_workflow",
        "input_lineage": {
            "decision": "operator_curated_local_file_or_api_payload",
            "audit_summary_present": audit_summary is not None,
            "thesis_status_present": thesis_status is not None,
        },
        "limitations": [
            "Decision Journal records research-process decisions only, not broker orders.",
            "Decision type is not buy/sell/hold and must remain process-oriented.",
            "The record preserves audit/thesis state at decision time without changing canonical outputs.",
        ],
        "not_investment_advice": True,
    }
    return record


def record_decision(
    decision: Mapping[str, Any],
    journal_path: str | Path,
    *,
    audit_summary: Mapping[str, Any] | None = None,
    thesis_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = build_decision_record(decision, audit_summary=audit_summary, thesis_status=thesis_status)
    if record.get("status") == "PASS":
        p = Path(journal_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def record_decision_from_files(
    decision_path: str | Path,
    journal_path: str | Path,
    *,
    audit_summary_path: str | Path | None = None,
    thesis_status_path: str | Path | None = None,
) -> dict[str, Any]:
    return record_decision(
        load_decision(decision_path),
        journal_path,
        audit_summary=load_json_artifact(audit_summary_path),
        thesis_status=load_json_artifact(thesis_status_path),
    )


def decision_to_files(
    decision_path: str | Path,
    journal_path: str | Path,
    output_dir: str | Path,
    *,
    audit_summary_path: str | Path | None = None,
    thesis_status_path: str | Path | None = None,
) -> dict[str, Any]:
    record = record_decision_from_files(
        decision_path,
        journal_path,
        audit_summary_path=audit_summary_path,
        thesis_status_path=thesis_status_path,
    )
    paths = write_decision_artifacts(record, output_dir, journal_path)
    return {"record": record, "paths": paths}


def write_decision_artifacts(record: Mapping[str, Any], output_dir: str | Path, journal_path: str | Path | None = None) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(record.get("ticker") or "UNKNOWN"))
    decision_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(record.get("decision_id") or "decision"))
    json_path = out / f"{ticker}_{decision_id}_decision_record.json"
    md_path = out / f"{ticker}_{decision_id}_decision_record.md"
    json_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_decision_record_md(record, journal_path=journal_path), encoding="utf-8")
    result = {"decision_record_json": str(json_path), "decision_record_report_md": str(md_path)}
    if journal_path:
        result["decision_journal_jsonl"] = str(journal_path)
    return result


def render_decision_record_md(record: Mapping[str, Any], *, journal_path: str | Path | None = None) -> str:
    lines = [
        "# Decision Journal Record",
        "",
        "## Verdict",
        "",
        f"- Status: `{record.get('status', 'UNKNOWN')}`",
        f"- Reason code: `{record.get('reason_code', 'UNKNOWN')}`",
        f"- Decision ID: `{record.get('decision_id', 'UNKNOWN')}`",
        f"- Ticker: `{record.get('ticker', 'UNKNOWN')}`",
        f"- Decision type: `{record.get('decision_type', 'UNKNOWN')}`",
        f"- Journal path: `{journal_path or 'not_persisted_by_api'}`",
        "",
        "## Captured audit state",
        "",
        f"- Data confidence at decision: `{record.get('data_confidence_at_decision', 'UNKNOWN')}`",
        f"- Model applicability at decision: `{record.get('model_applicability_at_decision', 'UNKNOWN')}`",
        f"- Conclusion risk at decision: `{record.get('conclusion_risk_at_decision', 'UNKNOWN')}`",
        f"- Thesis status at decision: `{record.get('thesis_status_at_decision', 'UNKNOWN')}`",
        "",
        "## Manual review items captured",
        "",
    ]
    for item in record.get("manual_review_items_at_decision") or ["No manual review items captured."]:
        lines.append(f"- {item}")
    lines += ["", "## Limitations", ""]
    for limitation in record.get("limitations") or []:
        lines.append(f"- {limitation}")
    return "\n".join(lines) + FOOTER


def load_journal(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    records = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _json_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _unknown_record(ticker: str, reason_code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": "decision_journal.v0.1",
        "sprint": "v4.0-p0.9",
        "status": "UNKNOWN",
        "reason_code": reason_code,
        "decision_id": None,
        "ticker": ticker or "UNKNOWN",
        "decision_type": "UNKNOWN",
        "manual_review_items_at_decision": [message],
        "source_quality": "UNKNOWN",
        "source_class": "operator_curated_research_workflow",
        "input_lineage": {"decision": "missing_or_invalid"},
        "limitations": ["Invalid decision records are not appended to the journal."],
        "not_investment_advice": True,
    }


def _safe_path(obj: Mapping[str, Any] | None, path: str) -> Any:
    cur: Any = obj or {}
    for part in path.split("."):
        if isinstance(cur, Mapping) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur
