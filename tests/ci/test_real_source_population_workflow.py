import subprocess
import sys


def test_real_source_population_workflow_gate_script_runs():
    result = subprocess.run(
        [sys.executable, "scripts/ci/check_real_source_population_workflow.py"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "production readiness is NOT_READY" in result.stdout or "Real-source registry reports PASS" in result.stdout
