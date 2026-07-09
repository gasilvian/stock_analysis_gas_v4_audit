#!/usr/bin/env python
"""Guard the real-source population workflow.

This script is intentionally conservative. It should pass in the repository's
baseline state only if production readiness is NOT_READY while required curated
files are missing/template/sample. It fails if the readiness gate accidentally
passes with placeholders.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sws_engine.sources.real_sources import validate_source_registry  # noqa: E402


def main() -> int:
    report = validate_source_registry(ROOT / "config/source_registry.yaml", require_production=True).as_dict()
    out_dir = ROOT / "validation" / "audit_final_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "real_source_population_workflow_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    if report["status"] == "PASS":
        print("ERROR: production readiness passed. Verify that curated real-source files are genuinely populated and marker-free.")
        # PASS is only acceptable if every required source is ready and no marker is present.
        bad = [s for s in report["sources"] if s.get("evaluated_required") and (s.get("looks_template_or_synthetic") or not s.get("ready"))]
        if bad:
            print(json.dumps(bad, indent=2))
            return 1
        print("Real-source registry reports PASS with all required sources ready.")
        return 0

    print("OK: production readiness is NOT_READY until real curated source files are populated.")
    print("Blocking issues:")
    for issue in report.get("blocking_issues", []):
        print(f"- {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
