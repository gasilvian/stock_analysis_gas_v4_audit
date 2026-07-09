#!/usr/bin/env python3
"""Gate: watchlist audit reports must preserve audit framing.

The report may triage workflow priority, but must not contain BUY/SELL/HOLD
recommendation language and must include the not-investment-advice footer.
"""
from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN = (" BUY ", " SELL ", " HOLD ", "STRONG BUY", "STRONG SELL")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_watchlist_report_guardrails.py <report-or-dir>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    reports = sorted(path.glob("*watchlist*report*.md")) if path.is_dir() else [path]
    if not reports:
        print(f"No watchlist report found under {path}", file=sys.stderr)
        return 1
    for report in reports:
        text = report.read_text(encoding="utf-8")
        if "Not investment advice" not in text:
            print(f"{report} missing not-investment-advice footer", file=sys.stderr)
            return 1
        for token in FORBIDDEN:
            if token in text.upper():
                print(f"{report} contains forbidden recommendation language: {token}", file=sys.stderr)
                return 1
    print("WATCHLIST_REPORT_GUARDRAILS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
