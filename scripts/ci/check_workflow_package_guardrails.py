#!/usr/bin/env python3
"""Governance gate for P0.13 workflow package/dashboard artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

FORBIDDEN = [" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "price target", "target price", "recommendation to", "rebalance into"]


def main(argv: list[str]) -> int:
    base = Path(argv[1]) if len(argv) > 1 else Path("out/p13_ci")
    if not base.exists():
        print(f"FAIL: workflow package output directory not found: {base}", file=sys.stderr)
        return 1
    json_files = list(base.rglob("*_workflow_package.json"))
    md_files = list(base.rglob("*_workflow_package_report.md"))
    if not json_files:
        print(f"FAIL: no *_workflow_package.json artifacts under {base}", file=sys.stderr)
        return 1
    failures: list[str] = []
    for path in json_files:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("schema_version") != "workflow_package.v0.1":
            failures.append(f"{path}: unexpected schema_version")
        if obj.get("not_investment_advice") is not True:
            failures.append(f"{path}: not_investment_advice must be true")
        if obj.get("recommendation_language_absent") is not True:
            failures.append(f"{path}: recommendation language guardrail failed")
        if not obj.get("component_status"):
            failures.append(f"{path}: component_status missing")
        if not obj.get("api_wiring"):
            failures.append(f"{path}: api_wiring missing")
        unknown_summary = obj.get("unknown_summary") or {}
        if unknown_summary.get("total_unknown_indicators") and "UNKNOWN" not in json.dumps(obj, sort_keys=True):
            failures.append(f"{path}: UNKNOWN appears to be hidden")
    for path in md_files:
        text = f" {path.read_text(encoding='utf-8')} "
        if "Not investment advice" not in text:
            failures.append(f"{path}: missing not-investment-advice footer")
        if "What remains UNKNOWN" not in text:
            failures.append(f"{path}: missing UNKNOWN section")
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{path}: forbidden recommendation token detected: {token.strip()}")
    if failures:
        for failure in failures:
            print("FAIL:", failure, file=sys.stderr)
        return 1
    print(f"PASS: workflow package guardrails OK for {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
