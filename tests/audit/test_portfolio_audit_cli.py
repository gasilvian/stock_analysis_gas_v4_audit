import json
import subprocess
import sys


def test_portfolio_audit_cli_smoke(tmp_path):
    out = tmp_path / "portfolio"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "portfolio-audit",
        "--holdings",
        "tests/fixtures/portfolio_audit/holdings.csv",
        "--audit-dir",
        "tests/fixtures/portfolio_audit/audits",
        "--business-risk-dir",
        "tests/fixtures/portfolio_audit/business_risks",
        "--thesis-dir",
        "tests/fixtures/portfolio_audit/theses",
        "--sensitivity-dir",
        "tests/fixtures/portfolio_audit/sensitivity",
        "--portfolio-id",
        "core",
        "--valuation-date",
        "2026-07-09",
        "--output",
        str(out),
    ]
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    body = json.loads(result.stdout)
    assert body["status"] == "PASS_WITH_LIMITATIONS"
    assert body["portfolio_id"] == "core"
    assert body["unknown_exposure_pct"] == 10.0
    assert (out / "core_portfolio_audit.json").exists()
    assert (out / "core_portfolio_audit_report.md").exists()
