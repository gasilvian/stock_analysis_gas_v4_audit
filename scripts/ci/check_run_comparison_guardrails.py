#!/usr/bin/env python3
"""Governance gate for P0.12 run comparison reports.

Fails if run-comparison artifacts hide UNKNOWN, omit the attribution/advice footer,
or contain forbidden recommendation language.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FORBIDDEN = [" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "price target", "target price", "recommendation to"]


def main(argv: list[str]) -> int:
    base = Path(argv[1]) if len(argv) > 1 else Path("out/p12_ci")
    if not base.exists():
        print(f"FAIL: run comparison output directory not found: {base}", file=sys.stderr)
        return 1
    json_files = list(base.rglob("*_run_comparison.json"))
    md_files = list(base.rglob("*_run_comparison_report.md"))
    if not json_files:
        print(f"FAIL: no *_run_comparison.json artifacts under {base}", file=sys.stderr)
        return 1
    failures: list[str] = []
    for path in json_files:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("schema_version") != "run_comparison.v0.1":
            failures.append(f"{path}: unexpected schema_version")
        if obj.get("not_investment_advice") is not True:
            failures.append(f"{path}: not_investment_advice must be true")
        if obj.get("recommendation_language_absent") is not True:
            failures.append(f"{path}: recommendation language guardrail failed")
        unknown_changes = obj.get("unknown_changes") or {}
        has_unknown = bool(
            unknown_changes.get("current_unknown_checks_count")
            or unknown_changes.get("critical_missing_inputs_current")
            or (obj.get("checks_changes") or {}).get("new_unknown_count")
        )
        text = json.dumps(obj, sort_keys=True)
        if has_unknown and "UNKNOWN" not in text:
            failures.append(f"{path}: UNKNOWN appears to be hidden")
        if obj.get("material_change_count") is None:
            failures.append(f"{path}: material_change_count missing")
    for path in md_files:
        text = f" {path.read_text(encoding='utf-8')} "
        if "Not investment advice" not in text:
            failures.append(f"{path}: missing not-investment-advice footer")
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{path}: forbidden recommendation token detected: {token.strip()}")
    if failures:
        for failure in failures:
            print("FAIL:", failure, file=sys.stderr)
        return 1
    print(f"PASS: run comparison guardrails OK for {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
