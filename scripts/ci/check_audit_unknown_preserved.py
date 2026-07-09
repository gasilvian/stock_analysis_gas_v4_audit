#!/usr/bin/env python3
"""Gate: audit artifacts must not hide UNKNOWN.

Usage:
  python scripts/ci/check_audit_unknown_preserved.py out/audit/AAPL
  python scripts/ci/check_audit_unknown_preserved.py out/audit/AAPL/*audit_summary*.json

The gate is intentionally simple: if the audit input has UNKNOWN checks, the
summary/report must expose `unknown_clusters` or the report text must contain
UNKNOWN.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _json_files(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("*audit_summary*.json"))
    return [path]


def check(path: Path) -> tuple[bool, str]:
    json_paths = _json_files(path)
    if not json_paths:
        return False, f"No audit_summary JSON found under {path}"
    for json_path in json_paths:
        try:
            obj = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"Could not parse {json_path}: {exc}"
        unknown_count = int(obj.get("data_confidence", {}).get("unknown_checks_count") or 0)
        clusters = obj.get("unknown_clusters") or obj.get("data_confidence", {}).get("unknown_clusters") or []
        if unknown_count > 0 and not clusters:
            return False, f"{json_path} has unknown_checks_count={unknown_count} but no unknown_clusters"
        report_candidates = sorted(json_path.parent.glob("*audit_report*.md"))
        if unknown_count > 0 and report_candidates:
            text = report_candidates[0].read_text(encoding="utf-8")
            if "UNKNOWN" not in text:
                return False, f"{report_candidates[0]} does not contain UNKNOWN despite unknown checks"
    return True, "UNKNOWN preservation gate PASS"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_audit_unknown_preserved.py <audit-dir-or-json>", file=sys.stderr)
        return 2
    ok, msg = check(Path(argv[1]))
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
