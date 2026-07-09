import json
import subprocess
import sys
from pathlib import Path


def test_explain_company_cli_from_output_json(tmp_path):
    output_path = tmp_path / "demo_output_unknown.json"
    out = json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))
    out["checks"][0]["result"] = "UNKNOWN"
    out["checks"][0]["reason_code"] = "MISSING_INPUT"
    out["checks"][0]["source_quality"] = "missing"
    output_path.write_text(json.dumps(out), encoding="utf-8")

    out_dir = tmp_path / "explain"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "explain-company",
        "--input",
        str(output_path),
        "--output",
        str(out_dir),
        "--mode",
        "analyst",
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, env={"PYTHONPATH": "src"})
    assert proc.returncode == 0, proc.stderr
    stdout = json.loads(proc.stdout)
    assert stdout["status"] == "PASS"
    assert stdout["checks_explained_count"] >= 1
    assert Path(stdout["explanations_json"]).exists()
    assert Path(stdout["explanation_report_md"]).exists()
