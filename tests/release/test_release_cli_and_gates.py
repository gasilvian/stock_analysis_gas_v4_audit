import json
import subprocess
import sys
from pathlib import Path


def test_release_package_cli_smoke(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sws_engine.cli",
            "release-package",
            "--repo-root",
            ".",
            "--release-id",
            "test-release",
            "--output",
            str(tmp_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["status"] == "MVP_COMPLETE_WITH_LIMITATIONS"
    assert body["production_readiness"] == "NOT_READY"
    assert Path(body["release_manifest_json"]).exists()


def test_check_release_manifest_gate_smoke(tmp_path):
    release = subprocess.run(
        [
            sys.executable,
            "-m",
            "sws_engine.cli",
            "release-package",
            "--repo-root",
            ".",
            "--release-id",
            "test-release",
            "--output",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(release.stdout)["status"] == "MVP_COMPLETE_WITH_LIMITATIONS"
    gate = subprocess.run(
        [sys.executable, "scripts/ci/check_release_manifest.py", str(tmp_path)],
        check=False,
        text=True,
        capture_output=True,
    )
    assert gate.returncode == 0, gate.stderr
    assert "PASS" in gate.stdout


def test_run_all_v4_gates_dry_run(tmp_path):
    output = tmp_path / "gates_report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/run_all_v4_gates.py",
            "--dry-run",
            "--output",
            str(output),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(output.read_text(encoding="utf-8"))
    assert body["schema_version"] == "v4_gate_report.v0.1"
    assert body["status"] == "PLANNED"
    assert body["not_investment_advice"] is True
