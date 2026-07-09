#!/usr/bin/env python3
"""Guardrail for P0.10 portfolio audit reports."""
from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN = [" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "Buy rating", "Sell rating", "Hold rating", "rebalance into", "overweight recommendation"]


def main(argv=None) -> int:
    args = list(argv or sys.argv[1:])
    roots = [Path(a) for a in args] if args else [Path("out")]
    checked = 0
    failures: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        files = [root] if root.is_file() else list(root.rglob("*.md"))
        for path in files:
            if "portfolio" not in path.name:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8")
            if "Not investment advice" not in text:
                failures.append(f"{path}: missing not-investment-advice footer")
            for token in FORBIDDEN:
                if token in text:
                    failures.append(f"{path}: forbidden recommendation token {token!r}")
    if failures:
        print("P0.10 portfolio audit guardrail failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"P0.10 portfolio audit guardrail PASS; checked={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
