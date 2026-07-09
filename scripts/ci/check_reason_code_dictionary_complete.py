#!/usr/bin/env python
"""Governance gate: every supported reason_code has deterministic templates."""
from __future__ import annotations

import argparse
import json
import sys

from sws_engine.explain.dictionary import validate_reason_code_dictionary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dictionary", default="config/reason_code_dictionary.yaml")
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)
    report = validate_reason_code_dictionary(args.dictionary)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
