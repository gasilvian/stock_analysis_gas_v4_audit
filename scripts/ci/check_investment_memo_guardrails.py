#!/usr/bin/env python3
"""Guardrail for P0.11 investment research audit memo outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

FORBIDDEN = [
    " BUY ",
    " SELL ",
    " HOLD ",
    "BUY/SELL/HOLD",
    "Buy rating",
    "Sell rating",
    "Hold rating",
    "price target",
    "target price",
    "recommendation to",
    "overweight recommendation",
    "underweight recommendation",
    "rebalance into",
]


def main(argv=None) -> int:
    args = list(argv or sys.argv[1:])
    roots = [Path(a) for a in args] if args else [Path("out")]
    checked = 0
    failures: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        files = [root] if root.is_file() else list(root.rglob("*memo*"))
        for path in files:
            if path.is_dir() or path.suffix.lower() not in {".md", ".json"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".md":
                if "Not investment advice" not in text:
                    failures.append(f"{path}: missing not-investment-advice footer")
                if "What remains UNKNOWN" not in text:
                    failures.append(f"{path}: missing UNKNOWN/limitations section")
            if path.suffix.lower() == ".json":
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError as exc:
                    failures.append(f"{path}: invalid JSON: {exc}")
                    continue
                if obj.get("schema_version") == "investment_memo.v0.1":
                    if obj.get("not_investment_advice") is not True:
                        failures.append(f"{path}: not_investment_advice must be true")
                    if obj.get("recommendation_language_absent") is not True:
                        failures.append(f"{path}: recommendation_language_absent must be true")
                    if not obj.get("unknown_summary"):
                        failures.append(f"{path}: unknown_summary missing")
            for token in FORBIDDEN:
                if token in text:
                    failures.append(f"{path}: forbidden recommendation token {token!r}")
    if failures:
        print("P0.11 investment memo guardrail failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"P0.11 investment memo guardrail PASS; checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
