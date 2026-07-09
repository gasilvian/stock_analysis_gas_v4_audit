#!/usr/bin/env python3
"""Run or enumerate v4.0 MVP governance gates.

Default mode executes the gates that can run offline in the local checkout. Use
--dry-run to produce a deterministic gate plan without executing subprocesses.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATES: list[list[str]] = [
    ["scripts/ci/check_lint_clean.py"],
    ["scripts/ci/validate_demo_outputs.py"],
    ["scripts/ci/check_no_score_normalized.py"],
    ["scripts/ci/check_attribution_footer.py"],
    ["scripts/ci/check_real_source_population_workflow.py"],
    ["scripts/ci/check_audit_unknown_preserved.py", "tests/fixtures/watchlist/audits"],
    ["scripts/ci/check_source_registry_field_rules.py"],
    ["scripts/ci/check_reason_code_dictionary_complete.py"],
    ["scripts/ci/check_watchlist_report_guardrails.py", "out/p08_ci"],
    ["scripts/ci/check_thesis_decision_guardrails.py", "out/p09_ci"],
    ["scripts/ci/check_portfolio_audit_guardrails.py", "out/p10_ci"],
    ["scripts/ci/check_investment_memo_guardrails.py", "out/p11_ci"],
    ["scripts/ci/check_run_comparison_guardrails.py", "out/p12_ci"],
    ["scripts/ci/check_workflow_package_guardrails.py", "out/p13_ci"],
    ["scripts/ci/check_release_manifest.py", "out/p14_ci"],
]


def _run_gate(repo_root: Path, command: list[str], *, dry_run: bool) -> dict[str, Any]:
    script = repo_root / command[0]
    name = Path(command[0]).name
    if not script.exists():
        return {"name": name, "command": command, "status": "NOT_RUN", "reason_code": "GATE_SCRIPT_MISSING"}
    for arg in command[1:]:
        if not (repo_root / arg).exists():
            return {"name": name, "command": command, "status": "NOT_RUN", "reason_code": "GATE_INPUT_MISSING", "missing_input": arg}
    if dry_run:
        return {"name": name, "command": command, "status": "PLANNED", "reason_code": "GATE_DRY_RUN"}
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, *command],
        cwd=str(repo_root),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return {
        "name": name,
        "command": command,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "reason_code": "GATE_PASSED" if result.returncode == 0 else "GATE_FAILED",
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v4.0 MVP governance gates")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="out/p14_ci/gates_report.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true", help="fail when any gate is NOT_RUN/PLANNED")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    rows = [_run_gate(repo_root, gate, dry_run=args.dry_run) for gate in GATES]
    failed = [row for row in rows if row["status"] == "FAIL"]
    not_run = [row for row in rows if row["status"] in {"NOT_RUN", "PLANNED"}]
    status = "PASS" if not failed and (not not_run or not args.strict) else "FAIL"
    if args.dry_run:
        status = "PLANNED" if not args.strict else "FAIL"
    report = {
        "schema_version": "v4_gate_report.v0.1",
        "sprint": "v4.0-p0.14",
        "status": status,
        "reason_code": "ALL_GATES_PASSED" if status == "PASS" else ("GATES_PLANNED" if status == "PLANNED" else "GATES_FAILED_OR_NOT_RUN"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gates": rows,
        "summary": {
            "total": len(rows),
            "passed": sum(1 for row in rows if row["status"] == "PASS"),
            "failed": len(failed),
            "not_run_or_planned": len(not_run),
        },
        "not_investment_advice": True,
    }
    out = repo_root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "reason_code": report["reason_code"], "output": str(out)}, indent=2))
    return 0 if report["status"] in {"PASS", "PLANNED"} and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
