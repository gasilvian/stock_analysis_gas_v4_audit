#!/usr/bin/env python3
"""Run the demo fixture through the engine and print the output JSON."""
import json
import sys

from sws_engine import run_company_analysis

fixture = sys.argv[1] if len(sys.argv) > 1 else \
    "tests/fixtures/demo_complete_non_financial.json"

with open(fixture, "r", encoding="utf-8") as fh:
    payload = json.load(fh)

output = run_company_analysis(
    payload,
    assumptions_path="config/assumptions.yaml",
    schema_path="schemas/output_schema.json",
    snapshot_dir="validation/snapshots",
)
print(json.dumps(output, indent=2))
