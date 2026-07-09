import json
import subprocess
import sys


def test_sensitivity_company_cli_from_input(tmp_path):
    out_dir = tmp_path / "sensitivity"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "sensitivity-company",
        "--input",
        "tests/fixtures/sensitivity/fcf_payload.json",
        "--output",
        str(out_dir),
        "--sensitivity-config",
        "config/sensitivity.yaml",
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, env={"PYTHONPATH": "src"})

    assert proc.returncode == 0, proc.stderr
    stdout = json.loads(proc.stdout)
    assert stdout["status"] in {"PASS", "PASS_WITH_LIMITATIONS"}
    assert stdout["sensitivity_summary_json"]
    assert stdout["sensitivity_report_md"]
    with open(stdout["sensitivity_summary_json"], "r", encoding="utf-8") as fh:
        summary = json.load(fh)
    assert summary["ticker"] == "SENS"
    assert summary["valuation_range"]["base"]["fair_value"] is not None
