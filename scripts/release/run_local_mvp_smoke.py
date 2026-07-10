#!/usr/bin/env python3
"""One-command local smoke run for the v4.0 MVP closure.

This smoke run is offline-only. It uses committed fixtures/artifacts and writes a
workflow package plus release manifest under out/p14_ci by default.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sws_engine.release.manifest import release_to_files
from sws_engine.research.workflow_package import workflow_package_to_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local v4.0 MVP smoke workflow")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="out/p14_ci")
    parser.add_argument("--release-id", default="v4.0-mvp-p0.14")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    out = root / args.output
    out.mkdir(parents=True, exist_ok=True)
    fix = root / "tests/fixtures/workflow_package"

    workflow = workflow_package_to_files(
        out / "workflow_smoke",
        audit_summary_path=fix / "AAPL_audit_summary.json",
        explanations_path=fix / "AAPL_explanations.json",
        sensitivity_path=fix / "AAPL_sensitivity_summary.json",
        business_risk_path=fix / "AAPL_business_risk_package.json",
        thesis_status_path=fix / "AAPL_thesis_status.json",
        decision_record_path=fix / "AAPL_decision_record.json",
        portfolio_audit_path=fix / "core_portfolio_audit.json",
        investment_memo_path=root / "out/p11_ci/AAPL_investment_audit_memo.json",
        run_comparison_path=root / "out/p12_ci/AAPL_run_comparison.json",
        workflow_id="p14-local-smoke",
    )

    # P2.7: readiness is computed live, never hardcoded — the manifest must
    # describe the build it ships, not the historical template era.
    from sws_engine.governance.legal_scope import validate_legal_scope
    from sws_engine.sources.real_sources import validate_source_registry
    legal = validate_legal_scope(str(root / "config/legal_scope.yaml")).as_dict()
    sources = validate_source_registry(str(root / "config/source_registry.yaml"),
                                       require_production=True).as_dict()
    readiness = "PASS" if legal["status"] == "PASS" and sources["status"] == "PASS" else "NOT_READY"
    release = release_to_files(
        out,
        repo_root=root,
        release_id=args.release_id,
        production_readiness=readiness,
    )
    summary = {
        "status": "PASS_WITH_LIMITATIONS",
        "reason_code": "RELEASE_LOCAL_SMOKE_COMPLETED",
        "workflow_package": workflow["paths"],
        "release": release["paths"],
        "production_readiness": release["manifest"]["scope_guardrails"]["production_readiness"],
        "not_investment_advice": True,
    }
    summary_path = out / "local_mvp_smoke_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "summary_path": str(summary_path), **release["paths"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
