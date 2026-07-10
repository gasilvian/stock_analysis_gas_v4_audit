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
    # P2.7: with live-computed readiness (PASS since P1.1) the status is
    # MVP_COMPLETE; both remain acceptable shapes of an honest manifest.
    assert body["status"] in ("MVP_COMPLETE", "MVP_COMPLETE_WITH_LIMITATIONS")
    # Readiness is live-computed and must be self-consistent with the same
    # evaluation the manifest gate performs — not pinned to an era.
    from sws_engine.governance.legal_scope import validate_legal_scope
    from sws_engine.sources.real_sources import validate_source_registry
    legal = validate_legal_scope("config/legal_scope.yaml").as_dict()
    sources = validate_source_registry("config/source_registry.yaml", require_production=True).as_dict()
    expected = "PASS" if legal["status"] == "PASS" and sources["status"] == "PASS" else "NOT_READY"
    assert body["production_readiness"] == expected
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
    # P2.7 update: readiness is computed live (default 'auto'). Since P1.1
    # all required curated sources are populated and operator-reviewed, so
    # the live evaluation yields PASS and the manifest status is
    # MVP_COMPLETE; the gate verifies the manifest against the same live
    # evaluation rather than pinning the template-era NOT_READY.
    assert json.loads(release.stdout)["status"] in ("MVP_COMPLETE", "MVP_COMPLETE_WITH_LIMITATIONS")
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
