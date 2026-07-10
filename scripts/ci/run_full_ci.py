#!/usr/bin/env python3
"""Unified local CI entrypoint (P2.7): lint + tests + gates + smoke, with evidence.

Runs, in order:
1. ruff (via the blocking check_lint_clean gate semantics),
2. the full offline pytest suite (tests/live excluded),
3. the v4 governance gate aggregator,
4. the local MVP release smoke (which rebuilds the release manifest).

Writes ``out/p14_ci/ci_evidence.json`` BEFORE the smoke step so the release
manifest embeds the evidence of the exact build it describes. Exit code is
non-zero if any stage fails — a release must never look green without its
proof.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "p14_ci"


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, check=False, **kw)


def stage_lint() -> dict:
    ruff = shutil.which("ruff")
    if ruff is None:
        return {"status": "FAIL", "reason_code": "RUFF_NOT_INSTALLED", "findings_count": None}
    res = _run([ruff, "check", ".", "--output-format", "concise"])
    if res.returncode == 0:
        return {"status": "PASS", "reason_code": "LINT_CLEAN", "findings_count": 0}
    findings = [line for line in res.stdout.splitlines()
                if line.strip() and not line.startswith(("Found ", "[*]"))]
    return {"status": "FAIL", "reason_code": "LINT_FINDINGS_PRESENT",
            "findings_count": len(findings)}


def stage_pytest() -> dict:
    env_prefix = ["env", "PYTHONPATH=src", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"]
    res = _run(env_prefix + [sys.executable, "-m", "pytest", "tests/", "-q", "--ignore=tests/live"])
    tail = (res.stdout or "").strip().splitlines()[-1] if res.stdout else ""
    counts = {key: int(num) for num, key in re.findall(r"(\d+) (passed|failed|skipped|error)", tail)}
    return {"status": "PASS" if res.returncode == 0 else "FAIL",
            "summary_line": tail,
            "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0),
            "skipped": counts.get("skipped", 0)}


def stage_gates() -> dict:
    res = _run(["env", "PYTHONPATH=src", sys.executable, "scripts/ci/run_all_v4_gates.py"])
    try:
        parsed = json.loads(res.stdout[res.stdout.index("{"):])
    except (ValueError, IndexError):
        parsed = {}
    return {"status": parsed.get("status", "FAIL" if res.returncode else "PASS"),
            "reason_code": parsed.get("reason_code")}


def stage_smoke() -> dict:
    res = _run(["env", "PYTHONPATH=src", sys.executable, "scripts/release/run_local_mvp_smoke.py"])
    try:
        parsed = json.loads(res.stdout[res.stdout.index("{"):])
    except (ValueError, IndexError):
        parsed = {}
    return {"status": parsed.get("status", "FAIL" if res.returncode else "PASS"),
            "release_manifest_json": parsed.get("release_manifest_json")}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema_version": "ci_evidence.v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lint": stage_lint(),
        "tests": stage_pytest(),
    }
    # Evidence (lint+tests) written BEFORE the smoke so the freshly built
    # release manifest embeds this build's proof; the smoke produces the
    # manifest, and the gate wall then validates it.
    (OUT / "ci_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    evidence["smoke"] = stage_smoke()
    evidence["gates"] = stage_gates()
    (OUT / "ci_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    failed = [name for name in ("lint", "tests", "gates") if evidence[name]["status"] == "FAIL"]
    if evidence["smoke"]["status"] not in ("PASS", "PASS_WITH_LIMITATIONS"):
        failed.append("smoke")
    status = "PASS" if not failed else "FAIL"
    print(json.dumps({
        "status": status,
        "reason_code": "FULL_CI_GREEN_WITH_EVIDENCE" if not failed else "FULL_CI_STAGE_FAILED",
        "failed_stages": failed,
        "evidence": str(OUT / "ci_evidence.json"),
        "lint_findings": evidence["lint"]["findings_count"],
        "tests_passed": evidence["tests"]["passed"],
        "gates": evidence["gates"]["status"],
        "smoke": evidence["smoke"]["status"],
    }, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
