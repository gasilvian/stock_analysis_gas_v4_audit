import json
import subprocess
import sys
from pathlib import Path


def test_business_risk_company_cli_from_input(tmp_path):
    out_dir = tmp_path / "business_risk"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "business-risk-company",
        "--input",
        "tests/fixtures/business_risk/risk_payload.json",
        "--output",
        str(out_dir),
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, env={"PYTHONPATH": "src"})
    assert proc.returncode == 0, proc.stderr
    stdout = json.loads(proc.stdout)
    assert stdout["status"] == "PASS_WITH_LIMITATIONS"
    assert stdout["red_flags_count"] >= 4
    assert Path(stdout["business_risk_package_json"]).exists()
    assert Path(stdout["business_risk_report_md"]).exists()
