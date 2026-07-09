#!/usr/bin/env python3
"""Governance gate: repository must be lint-clean (ruff, zero findings).

P1.0 remediation gate. The v4.0 P0.x series accumulated 14 ruff findings
because ruff was not available in the implementation sandbox. This gate makes
lint cleanliness a blocking condition so hygiene regressions cannot accumulate
silently again.

Behavior:
- If ruff is importable/executable, run `ruff check .` at the repo root.
  Any finding -> FAIL / LINT_FINDINGS_PRESENT.
- If ruff is not installed, the gate FAILS with RUFF_NOT_INSTALLED. This is
  intentional: an environment that cannot verify lint cleanliness must not
  report a passing gate wall. Install ruff (dev dependency) to run gates.

This gate is audit-layer governance only. It does not modify engine behavior,
output_schema.json, checks, valuation, growth, portfolio or assumptions.yaml.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(argv[0]).resolve() if argv else Path(".").resolve()
    ruff = shutil.which("ruff")
    if ruff is None:
        report = {
            "gate": "check_lint_clean",
            "status": "FAIL",
            "reason_code": "RUFF_NOT_INSTALLED",
            "detail": "ruff executable not found; install dev dependency `ruff` to run this blocking gate",
        }
        print(json.dumps(report, indent=2))
        return 1

    result = subprocess.run(
        [ruff, "check", ".", "--output-format", "concise"],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    findings = [
        line
        for line in result.stdout.splitlines()
        if line.strip() and not line.startswith(("Found ", "[*]"))
    ]
    if result.returncode == 0:
        report = {
            "gate": "check_lint_clean",
            "status": "PASS",
            "reason_code": "LINT_CLEAN",
            "findings_count": 0,
        }
        print(json.dumps(report, indent=2))
        return 0

    report = {
        "gate": "check_lint_clean",
        "status": "FAIL",
        "reason_code": "LINT_FINDINGS_PRESENT",
        "findings_count": len(findings),
        "findings_sample": findings[:20],
    }
    print(json.dumps(report, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
