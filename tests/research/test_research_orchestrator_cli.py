"""P2.1 CLI surface tests for ``research-company`` (offline, demo payload)."""
import json
from pathlib import Path

import pytest

from sws_engine.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[2]
DEMO_PAYLOAD = ROOT / "tests" / "fixtures" / "demo_complete_non_financial.json"


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    return tmp_path


def test_cli_offline_chain_exit_code_and_stdout(workdir, capsys):
    db = workdir / "cli.db"
    out = workdir / "out"
    rc = cli_main([
        "research-company",
        "--input", str(DEMO_PAYLOAD),
        "--db", str(db),
        "--output", str(out),
    ])
    # Sensitivity is honestly UNKNOWN on the demo payload -> exit code 2
    # (PASS_WITH_LIMITATIONS), mirroring the single-command convention.
    assert rc == 2
    stdout = capsys.readouterr().out
    summary = json.loads(stdout)
    assert summary["status"] == "PASS_WITH_LIMITATIONS"
    assert summary["steps"]["engine"] == "PASS"
    assert summary["steps"]["sensitivity"] == "UNKNOWN"
    assert summary["steps"]["memo"] == "PASS"
    assert "sensitivity" in summary["unknown_steps"]
    assert Path(summary["research_company_run_json"]).exists()
    assert Path(summary["research_company_run_md"]).exists()


def test_cli_requires_exactly_one_mode(workdir, capsys):
    rc = cli_main([
        "research-company",
        "--db", str(workdir / "x.db"),
        "--output", str(workdir / "out"),
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "exactly one of" in err


def test_cli_missing_payload_exits_1(workdir, capsys):
    rc = cli_main([
        "research-company",
        "--input", str(workdir / "nope.json"),
        "--db", str(workdir / "x.db"),
        "--output", str(workdir / "out"),
    ])
    assert rc == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "FAIL"
    assert summary["reason_code"] == "RESEARCH_CHAIN_INPUT_MISSING"
