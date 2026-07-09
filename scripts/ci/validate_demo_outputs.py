"""Generate representative demo outputs and validate them against the schema."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sws_engine.orchestration.company_run import run_company_analysis

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    schema_path = ROOT / "schemas/output_schema.json"
    assumptions_path = ROOT / "config/assumptions.yaml"
    payload_path = ROOT / "tests/fixtures/demo_complete_non_financial.json"
    out_dir = ROOT / "validation/snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    output = run_company_analysis(payload, str(assumptions_path), str(schema_path))
    Draft202012Validator(schema).validate(output)
    out_path = out_dir / "ci_demo_company_output.json"
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"validated": str(out_path), "checks": len(output.get("checks", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
