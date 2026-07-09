import json
import subprocess
import sys
from pathlib import Path

FIX = Path("tests/fixtures/run_comparison")


def test_compare_runs_cli_smoke(tmp_path):
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "compare-runs",
        "--previous",
        str(FIX / "AAPL_previous_audit_summary.json"),
        "--current",
        str(FIX / "AAPL_current_audit_summary.json"),
        "--comparison-id",
        "cli-aapl-p12",
        "--output",
        str(tmp_path),
    ]
    result = subprocess.run(cmd, text=True, capture_output=True, check=True)
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS_WITH_LIMITATIONS"
    assert payload["reason_code"] == "RUN_COMPARISON_UNKNOWN_PRESERVED"
    assert Path(payload["comparison_json"]).exists()
    assert Path(payload["comparison_report"]).exists()
