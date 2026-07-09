import json
import subprocess
import sys
from pathlib import Path


def test_thesis_status_cli(tmp_path):
    out_dir = tmp_path / "thesis"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "thesis-status",
        "--thesis",
        "tests/fixtures/thesis_decision/AAPL_thesis.yaml",
        "--audit-summary",
        "tests/fixtures/thesis_decision/AAPL_audit_summary.json",
        "--output",
        str(out_dir),
    ]
    res = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["status"] == "PASS_WITH_LIMITATIONS"
    assert body["thesis_status"] == "ON_TRACK"
    assert Path(body["thesis_status_json"]).exists()
    assert Path(body["thesis_status_report_md"]).exists()


def test_record_decision_cli(tmp_path):
    out_dir = tmp_path / "decision"
    journal = tmp_path / "decisions" / "decisions.jsonl"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "record-decision",
        "--decision",
        "tests/fixtures/thesis_decision/AAPL_decision.yaml",
        "--journal",
        str(journal),
        "--audit-summary",
        "tests/fixtures/thesis_decision/AAPL_audit_summary.json",
        "--output",
        str(out_dir),
    ]
    res = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["status"] == "PASS"
    assert body["decision_type"] == "research_deeper"
    assert Path(body["decision_record_json"]).exists()
    assert Path(body["decision_record_report_md"]).exists()
    assert Path(body["decision_journal_jsonl"]).exists()
