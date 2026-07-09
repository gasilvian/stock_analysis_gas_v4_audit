import json
import subprocess
import sys
from pathlib import Path

FIX = Path("tests/fixtures/workflow_package")


def test_workflow_package_cli_smoke(tmp_path):
    out = tmp_path / "workflow"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sws_engine.cli",
            "workflow-package",
            "--audit-summary",
            str(FIX / "AAPL_audit_summary.json"),
            "--explanations",
            str(FIX / "AAPL_explanations.json"),
            "--sensitivity",
            str(FIX / "AAPL_sensitivity_summary.json"),
            "--business-risk",
            str(FIX / "AAPL_business_risk_package.json"),
            "--thesis-status",
            str(FIX / "AAPL_thesis_status.json"),
            "--decision-record",
            str(FIX / "AAPL_decision_record.json"),
            "--portfolio-audit",
            str(FIX / "core_portfolio_audit.json"),
            "--run-comparison",
            str(FIX / "AAPL_run_comparison.json"),
            "--workflow-id",
            "p13-aapl",
            "--output",
            str(out),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert body["ticker"] == "AAPL"
    assert body["workflow_id"] == "p13-aapl"
    assert body["recommendation_language_absent"] is True
    assert Path(body["workflow_package_json"]).exists()
