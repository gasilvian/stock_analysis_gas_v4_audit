"""P0.14 release hardening and MVP closure manifest.

The release manifest is an additive governance artifact. It does not modify the
v3.1 engine, does not fetch live data, does not declare production readiness,
and does not contain investment recommendation language.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from sws_engine.governance.guardrail_tokens import FORBIDDEN_RECOMMENDATION_TOKENS

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

# P1.0: FORBIDDEN_RECOMMENDATION_TOKENS moved to sws_engine.governance.guardrail_tokens

REQUIRED_CAPABILITY_GROUPS = [
    {
        "id": "core_contract_governance",
        "label": "Core v3.1 contract and governance files",
        "required_files": [
            "schemas/output_schema.json",
            "config/assumptions.yaml",
            "config/source_registry.yaml",
            "config/legal_scope.yaml",
            "legal/NOTICE.md",
        ],
    },
    {
        "id": "audit_core",
        "label": "Company audit, data confidence and model applicability",
        "required_files": [
            "src/sws_engine/audit/audit_summary.py",
            "src/sws_engine/audit/data_confidence.py",
            "src/sws_engine/audit/model_applicability.py",
            "src/sws_engine/audit/conclusion_risk.py",
            "schemas/aux/audit_summary.schema.json",
        ],
    },
    {
        "id": "sec_rates_reference",
        "label": "SEC-first, curated rates and Identifier Master foundation",
        "required_files": [
            "src/sws_engine/sec/workflow.py",
            "src/sws_engine/sec/statement_snapshot.py",
            "src/sws_engine/rates/curated.py",
            "src/sws_engine/reference/identifier_master.py",
        ],
    },
    {
        "id": "sensitivity_explainability",
        "label": "Sensitivity and deterministic reason-code explainability",
        "required_files": [
            "src/sws_engine/sensitivity/scenario_runner.py",
            "src/sws_engine/sensitivity/reverse_dcf.py",
            "src/sws_engine/explain/check_explainer.py",
            "config/reason_code_dictionary.yaml",
            "schemas/aux/sensitivity_summary.schema.json",
            "schemas/aux/explanation_package.schema.json",
        ],
    },
    {
        "id": "business_risk",
        "label": "Red flags, accounting quality and capital allocation signals",
        "required_files": [
            "src/sws_engine/audit/risk_signals.py",
            "schemas/aux/business_risk_package.schema.json",
        ],
    },
    {
        "id": "research_discipline",
        "label": "Watchlist audit, thesis tracker and decision journal",
        "required_files": [
            "src/sws_engine/research/watchlist.py",
            "src/sws_engine/research/thesis.py",
            "src/sws_engine/research/journal.py",
            "schemas/aux/watchlist_audit.schema.json",
            "schemas/aux/thesis_status.schema.json",
            "schemas/aux/decision_journal.schema.json",
        ],
    },
    {
        "id": "portfolio_and_memo",
        "label": "Portfolio audit and investment audit memo",
        "required_files": [
            "src/sws_engine/audit/portfolio_audit.py",
            "src/sws_engine/reporting/investment_memo.py",
            "schemas/aux/portfolio_audit.schema.json",
            "schemas/aux/investment_memo.schema.json",
        ],
    },
    {
        "id": "change_detection_and_workflow",
        "label": "Run comparison and dashboard/API workflow package",
        "required_files": [
            "src/sws_engine/research/run_comparison.py",
            "src/sws_engine/research/workflow_package.py",
            "dashboard/pages/6_Audit_Workflow_Hub.py",
            "dashboard/components/audit_workflow.py",
            "schemas/aux/run_comparison.schema.json",
            "schemas/aux/workflow_package.schema.json",
        ],
    },
    {
        "id": "release_closure",
        "label": "Release hardening and local operator closure",
        "required_files": [
            "src/sws_engine/release/manifest.py",
            "schemas/aux/release_manifest.schema.json",
            "docs/release_v4_mvp.md",
            "docs/local_operator_runbook.md",
            "scripts/ci/check_release_manifest.py",
            "scripts/ci/run_all_v4_gates.py",
            "scripts/release/run_local_mvp_smoke.py",
            "examples/workflows/full_company_research_flow/README.md",
        ],
    },
]

KNOWN_LIMITATIONS = [
    "Production readiness remains NOT_READY until curated real-source files are populated and reviewed.",
    "The MVP is offline-first and fixture-driven for CI; it does not fetch live data as part of release validation.",
    "Full source-conflict runtime resolution remains deferred; no silent source blending is allowed.",
    "Sector-specific bank, REIT and insurer workflows remain limited to foundation-level handling.",
    "Transaction-based performance attribution, optimization, broker integration and action-oriented language remain outside MVP scope.",
    "Missing or unevaluable data remains UNKNOWN and must not be inferred from similar fields.",
]

ARTIFACT_INDEX = [
    "out/p08_ci/watchlist_audit.json",
    "out/p09_ci/thesis/AAPL_thesis_status.json",
    "out/p09_ci/decision/AAPL_dec_23305b9d36b1_decision_record.json",
    "out/p10_ci/core_portfolio_audit.json",
    "out/p11_ci/AAPL_investment_audit_memo.json",
    "out/p12_ci/AAPL_run_comparison.json",
    "out/p13_ci/AAPL_workflow_package.json",
]

GOVERNANCE_GATES = [
    "validate_demo_outputs.py",
    "check_no_" + "score_" + "normalized.py",
    "check_attribution_footer.py",
    "check_real_source_population_workflow.py",
    "check_audit_unknown_preserved.py",
    "check_source_registry_field_rules.py",
    "check_reason_code_dictionary_complete.py",
    "check_watchlist_report_guardrails.py",
    "check_thesis_decision_guardrails.py",
    "check_portfolio_audit_guardrails.py",
    "check_investment_memo_guardrails.py",
    "check_run_comparison_guardrails.py",
    "check_workflow_package_guardrails.py",
    "check_release_manifest.py",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_value(repo_root: Path, args: list[str]) -> str:
    try:
        res = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


def _file_status(repo_root: Path, rel_path: str) -> dict[str, Any]:
    path = repo_root / rel_path
    return {
        "path": rel_path,
        "exists": path.exists(),
        "source_quality": "exact" if path.exists() else "missing",
        "source_class": "E0" if path.exists() else "UNKNOWN",
    }


def _capability_status(repo_root: Path, group: Mapping[str, Any]) -> dict[str, Any]:
    required = list(group.get("required_files") or [])
    statuses = [_file_status(repo_root, p) for p in required]
    missing = [row["path"] for row in statuses if not row["exists"]]
    return {
        "id": group["id"],
        "label": group["label"],
        "status": "PASS" if not missing else "UNKNOWN",
        "reason_code": "RELEASE_CAPABILITY_PRESENT" if not missing else "RELEASE_CAPABILITY_ARTIFACT_MISSING",
        "required_files_count": len(required),
        "missing_files_count": len(missing),
        "missing_files": missing,
        "input_lineage": statuses,
    }


def _validation_reports(repo_root: Path, validation_dir: str) -> list[dict[str, Any]]:
    path = repo_root / validation_dir
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for report in sorted(path.glob("validation_report_v4_p0_*.md")):
        text = report.read_text(encoding="utf-8", errors="ignore")
        rows.append({
            "path": str(report.relative_to(repo_root)),
            "exists": True,
            "declared_pass_with_limitations": "PASS WITH LIMITATIONS" in text,
            "declared_not_ready": "NOT_READY" in text,
            "declared_not_investment_advice": "Not investment advice" in text or "not investment advice" in text.lower(),
            "source_quality": "exact",
            "source_class": "E0",
        })
    return rows


def _artifact_index(repo_root: Path, artifact_paths: Iterable[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel_path in list(artifact_paths or ARTIFACT_INDEX):
        rows.append(_file_status(repo_root, rel_path))
    return rows


def _contains_forbidden_recommendation(text: str) -> bool:
    padded = f" {text} "
    return any(token in padded for token in FORBIDDEN_RECOMMENDATION_TOKENS)


def build_release_manifest(
    *,
    repo_root: str | Path = ".",
    release_id: str | None = None,
    validation_dir: str = "validation",
    production_readiness: str = "NOT_READY",
    artifact_paths: Iterable[str] | None = None,
    gates_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the v4.0 MVP release manifest from local repository evidence."""
    root = Path(repo_root).resolve()
    capability_rows = [_capability_status(root, group) for group in REQUIRED_CAPABILITY_GROUPS]
    missing_capability_count = sum(1 for row in capability_rows if row["status"] != "PASS")
    validation_rows = _validation_reports(root, validation_dir)
    artifact_rows = _artifact_index(root, artifact_paths)
    missing_artifact_count = sum(1 for row in artifact_rows if not row["exists"])

    status = "MVP_COMPLETE_WITH_LIMITATIONS"
    reason_code = "RELEASE_MVP_COMPLETE_WITH_LIMITATIONS"
    if missing_capability_count:
        status = "BLOCKED"
        reason_code = "RELEASE_REQUIRED_ARTIFACT_MISSING"
    elif production_readiness == "PASS":
        status = "MVP_COMPLETE"
        reason_code = "RELEASE_MVP_COMPLETE"

    # P2.7: a green release must carry its own proof. When the unified CI
    # entrypoint produced evidence (out/p14_ci/ci_evidence.json), embed it;
    # otherwise state honestly that no evidence was provided.
    evidence_path = root / "out" / "p14_ci" / "ci_evidence.json"
    if evidence_path.exists():
        try:
            quality_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            quality_evidence = {"status": "EVIDENCE_UNREADABLE", "path": str(evidence_path)}
    else:
        quality_evidence = {"status": "NOT_PROVIDED",
                            "note": "run scripts/ci/run_full_ci.py to generate ruff/pytest/gates evidence"}

    gate_summary = gates_report or {
        "status": "NOT_RUN",
        "reason_code": "RELEASE_GATES_NOT_RUN",
        "gates": [{"name": name, "status": "NOT_RUN"} for name in GOVERNANCE_GATES],
    }

    manifest = {
        "schema_version": "release_manifest.v0.1",
        "sprint": "v4.0-p0.14",
        "release_id": release_id or "v4.0-mvp-p0.14",
        "status": status,
        "reason_code": reason_code,
        "generated_at": _utc_now(),
        "repository": {
            "root": str(root),
            "branch": _git_value(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
            "commit": _git_value(root, ["rev-parse", "--short", "HEAD"]),
            "dirty_status": _git_value(root, ["status", "--short"]),
        },
        "scope_guardrails": {
            "usage_scope": "internal_personal_educational",
            "commercial_use_enabled": False,
            "external_access_enabled": False,
            "legal_review_completed": False,
            "not_investment_advice": True,
            "production_readiness": production_readiness,
            "output_schema_unchanged_policy": True,
            "unknown_policy_preserved": True,
            "provider_degradation_visible_policy": True,
            "recommendation_language_absent": True,
        },
        "capabilities": capability_rows,
        "capability_summary": {
            "total": len(capability_rows),
            "pass": sum(1 for row in capability_rows if row["status"] == "PASS"),
            "unknown_or_missing": missing_capability_count,
        },
        "validation_reports": validation_rows,
        "validation_summary": {
            "reports_found": len(validation_rows),
            "p0_reports_found": len([r for r in validation_rows if "validation_report_v4_p0_" in r["path"]]),
        },
        "artifact_index": artifact_rows,
        "artifact_summary": {
            "artifacts_indexed": len(artifact_rows),
            "missing_artifacts": missing_artifact_count,
        },
        "gate_summary": gate_summary,
        "quality_evidence": quality_evidence,
        "known_limitations": KNOWN_LIMITATIONS,
        "next_phase": {
            "recommended_phase": "P1.0 production data population",
            "reason": "MVP feature closure is complete with limitations; curated real-source population remains required before production-readiness can pass.",
        },
        "manual_review_items": _manual_review_items(
            missing_capability_count=missing_capability_count,
            missing_artifact_count=missing_artifact_count,
            production_readiness=production_readiness,
            gates_report=gate_summary,
        ),
        "not_investment_advice": True,
    }
    return manifest


def _manual_review_items(
    *,
    missing_capability_count: int,
    missing_artifact_count: int,
    production_readiness: str,
    gates_report: Mapping[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if missing_capability_count:
        items.append({
            "reason_code": "RELEASE_REQUIRED_ARTIFACT_MISSING",
            "message": f"{missing_capability_count} required release capability group(s) have missing files.",
        })
    if missing_artifact_count:
        items.append({
            "reason_code": "RELEASE_OPTIONAL_ARTIFACT_MISSING",
            "message": f"{missing_artifact_count} indexed workflow artifact(s) are absent; keep them visible rather than inferred.",
        })
    if production_readiness != "PASS":
        items.append({
            "reason_code": "RELEASE_PRODUCTION_NOT_READY",
            "message": "Production readiness is not passed because curated real-source files still require population and review.",
        })
    if gates_report.get("status") not in {"PASS", "OK"}:
        items.append({
            "reason_code": "RELEASE_GATES_NOT_RUN",
            "message": "Aggregated release gates are not all confirmed PASS in the supplied manifest context.",
        })
    return items


def render_release_report_md(manifest: Mapping[str, Any]) -> str:
    """Render a deterministic release closure report."""
    lines = [
        f"# v4.0 MVP Release Closure — {manifest.get('release_id')}",
        "",
        f"Status: `{manifest.get('status')}`",
        f"Reason code: `{manifest.get('reason_code')}`",
        f"Sprint: `{manifest.get('sprint')}`",
        f"Generated at: `{manifest.get('generated_at')}`",
        "",
        "## Scope guardrails",
        "",
    ]
    guardrails = manifest.get("scope_guardrails") or {}
    for key in [
        "usage_scope",
        "production_readiness",
        "commercial_use_enabled",
        "external_access_enabled",
        "legal_review_completed",
        "not_investment_advice",
        "unknown_policy_preserved",
        "provider_degradation_visible_policy",
    ]:
        lines.append(f"- {key}: `{guardrails.get(key)}`")
    lines.extend(["", "## Capability closure", "", "| Capability | Status | Missing files |", "|---|---:|---:|"])
    for row in manifest.get("capabilities") or []:
        missing = row.get("missing_files_count", 0)
        lines.append(f"| {row.get('label')} | {row.get('status')} | {missing} |")
    summary = manifest.get("capability_summary") or {}
    lines.extend([
        "",
        f"Capability groups passed: `{summary.get('pass')}/{summary.get('total')}`.",
        "",
        "## Validation and gate evidence",
        "",
    ])
    validation_summary = manifest.get("validation_summary") or {}
    gate_summary = manifest.get("gate_summary") or {}
    lines.extend([
        f"- validation reports found: `{validation_summary.get('reports_found')}`",
        f"- P0 validation reports found: `{validation_summary.get('p0_reports_found')}`",
        f"- aggregated gate status: `{gate_summary.get('status')}`",
        f"- aggregated gate reason_code: `{gate_summary.get('reason_code')}`",
        "",
        "## Indexed MVP artifacts",
        "",
        "| Artifact | Exists |",
        "|---|---:|",
    ])
    for row in manifest.get("artifact_index") or []:
        lines.append(f"| `{row.get('path')}` | `{row.get('exists')}` |")
    lines.extend(["", "## What remains UNKNOWN or limited", ""])
    for item in manifest.get("manual_review_items") or []:
        lines.append(f"- `{item.get('reason_code')}` — {item.get('message')}")
    if not manifest.get("manual_review_items"):
        lines.append("- No manifest-level manual review items.")
    lines.extend(["", "## Known limitations", ""])
    for limitation in manifest.get("known_limitations") or []:
        lines.append(f"- {limitation}")
    lines.extend([
        "",
        "## Next phase",
        "",
        f"Recommended phase: `{(manifest.get('next_phase') or {}).get('recommended_phase')}`.",
        (manifest.get("next_phase") or {}).get("reason") or "",
        "",
        "This release closure is a decision-hygiene and research-audit artifact. It is not an economic conclusion and does not instruct any investment action.",
    ])
    text = "\n".join(lines) + FOOTER
    if _contains_forbidden_recommendation(text):
        raise ValueError("Release report contains forbidden recommendation-language token")
    return text


def write_release_artifacts(manifest: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    release_id = str(manifest.get("release_id") or "release").replace("/", "_")
    json_path = out / f"{release_id}_release_manifest.json"
    md_path = out / f"{release_id}_release_report.md"
    json_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    md_path.write_text(render_release_report_md(manifest), encoding="utf-8")
    return {"release_manifest_json": str(json_path), "release_report_md": str(md_path)}


def release_to_files(
    output_dir: str | Path,
    *,
    repo_root: str | Path = ".",
    release_id: str | None = None,
    validation_dir: str = "validation",
    production_readiness: str = "NOT_READY",
    artifact_paths: Iterable[str] | None = None,
    gates_report_path: str | Path | None = None,
) -> dict[str, Any]:
    gates_report = None
    if gates_report_path and Path(gates_report_path).exists():
        gates_report = json.loads(Path(gates_report_path).read_text(encoding="utf-8"))
    manifest = build_release_manifest(
        repo_root=repo_root,
        release_id=release_id,
        validation_dir=validation_dir,
        production_readiness=production_readiness,
        artifact_paths=artifact_paths,
        gates_report=gates_report,
    )
    paths = write_release_artifacts(manifest, output_dir)
    return {"manifest": manifest, "paths": paths}
