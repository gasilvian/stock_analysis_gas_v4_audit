"""Audit summary composition for existing v3.1 outputs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

import sws_engine
from sws_engine.audit.conclusion_risk import assess_conclusion_risk
from sws_engine.audit.data_confidence import assess_data_confidence
from sws_engine.audit.model_applicability import assess_model_applicability
from sws_engine.audit.policies import load_audit_policies, load_source_registry


def build_audit_summary(
    output: Dict[str, Any],
    *,
    run_id: str | None = None,
    input_payload: Dict[str, Any] | None = None,
    assumptions_hash: str | None = None,
    engine_version: str | None = None,
    output_schema_version: str = "v3.1",
    audit_policies_path: str | None = None,
    source_registry_path: str | None = None,
    identifier_master_path: str | None = None,
) -> Dict[str, Any]:
    audit_policies = load_audit_policies(audit_policies_path or "config/audit_policies.yaml")
    source_registry = load_source_registry(source_registry_path or "config/source_registry.yaml")
    data_conf = assess_data_confidence(
        output,
        input_payload=input_payload,
        audit_policies=audit_policies,
        source_registry=source_registry,
    )
    applicability = assess_model_applicability(
        output,
        input_payload=input_payload,
        audit_policies=audit_policies,
        identifier_master_path=identifier_master_path,
    )
    risk = assess_conclusion_risk(output, data_confidence=data_conf, model_applicability=applicability)
    warnings = list(output.get("warnings") or [])
    if data_conf.get("warnings"):
        warnings.extend(w for w in data_conf["warnings"] if w not in warnings)
    return {
        "schema_version": "audit_summary.v0.2",
        "engine_version": engine_version or sws_engine.__version__,
        "output_schema_version": output_schema_version,
        "run_id": run_id,
        "input_snapshot_id": _input_snapshot_id(input_payload),
        "assumptions_hash": assumptions_hash or _assumptions_hash_from_output(output),
        "ticker": output.get("ticker", "UNKNOWN"),
        "exchange": output.get("exchange", "UNKNOWN"),
        "valuation_date": output.get("valuation_date", "UNKNOWN"),
        "provider_profile": output.get("provider_profile", "UNKNOWN"),
        "score_summary": _score_summary(output),
        "checks_summary": _checks_summary(output),
        "data_confidence": data_conf,
        "model_applicability": applicability,
        "conclusion_risk": risk,
        "critical_missing_inputs": data_conf.get("critical_missing_inputs", []),
        "unknown_clusters": data_conf.get("unknown_clusters", []),
        "warnings": warnings,
        "provider_degradation_visible": data_conf.get("provider_degradation_visible", False),
        "not_investment_advice": True,
        "policy_version": data_conf.get("policy_version"),
        "lineage": {
            "output_lineage": output.get("lineage", {}),
            "input_lineage_summary": data_conf.get("input_lineage_summary", {}),
        },
    }


def load_latest_audit_context_from_db(db_path: str, ticker: str, run_id: str | None = None) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if run_id:
            row = conn.execute(
                """SELECT r.run_id, r.snapshot_id, r.assumptions_hash, r.engine_version, o.output_json,
                          i.payload_json
                   FROM outputs o
                   JOIN runs r ON o.run_id=r.run_id
                   LEFT JOIN input_snapshots i ON r.snapshot_id=i.snapshot_id
                   WHERE o.run_id=? AND o.ticker=?""",
                (run_id, ticker),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT r.run_id, r.snapshot_id, r.assumptions_hash, r.engine_version, o.output_json,
                          i.payload_json
                   FROM outputs o
                   JOIN runs r ON o.run_id=r.run_id
                   LEFT JOIN input_snapshots i ON r.snapshot_id=i.snapshot_id
                   WHERE o.ticker=?
                   ORDER BY o.valuation_date DESC, o.rowid DESC LIMIT 1""",
                (ticker,),
            ).fetchone()
        if not row:
            raise FileNotFoundError(f"No persisted company output found for ticker '{ticker}'.")
        output = json.loads(row["output_json"])
        input_payload = json.loads(row["payload_json"]) if row["payload_json"] else None
        return {
            "run_id": row["run_id"],
            "snapshot_id": row["snapshot_id"],
            "assumptions_hash": row["assumptions_hash"],
            "engine_version": row["engine_version"],
            "output": output,
            "input_payload": input_payload,
        }
    finally:
        conn.close()


def build_audit_summary_from_db(
    db_path: str,
    ticker: str,
    run_id: str | None = None,
    *,
    audit_policies_path: str | None = None,
    source_registry_path: str | None = None,
    identifier_master_path: str | None = None,
) -> Dict[str, Any]:
    ctx = load_latest_audit_context_from_db(db_path, ticker, run_id=run_id)
    summary = build_audit_summary(
        ctx["output"],
        run_id=ctx["run_id"],
        input_payload=ctx["input_payload"],
        assumptions_hash=ctx["assumptions_hash"],
        engine_version=ctx["engine_version"],
        audit_policies_path=audit_policies_path,
        source_registry_path=source_registry_path,
        identifier_master_path=identifier_master_path,
    )
    if ctx.get("snapshot_id"):
        summary["input_snapshot_id"] = ctx["snapshot_id"]
    return summary


def write_json(path: str | Path, obj: Dict[str, Any]) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    return str(p)


def _input_snapshot_id(input_payload: Optional[Dict[str, Any]]) -> str | None:
    if not input_payload:
        return None
    return input_payload.get("snapshot_id") or input_payload.get("input_snapshot_id")


def _assumptions_hash_from_output(output: Dict[str, Any]) -> str | None:
    lineage = output.get("lineage") or {}
    return output.get("assumptions_hash") or lineage.get("assumptions_hash")


def _score_summary(output: Dict[str, Any]) -> Dict[str, Any]:
    summary: dict[str, Any] = {}
    for axis, score in (output.get("scores") or {}).items():
        summary[axis] = {
            "score_raw": score.get("score_raw"),
            "coverage_pct": score.get("coverage_pct"),
            "known_checks_count": score.get("known_checks_count"),
            "unknown_checks_count": score.get("unknown_checks_count"),
        }
    return summary


def _checks_summary(output: Dict[str, Any]) -> Dict[str, int]:
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0}
    for check in output.get("checks", []) or []:
        result = check.get("result", "UNKNOWN")
        counts[result] = counts.get(result, 0) + 1
    counts["total"] = sum(counts.values())
    return counts
