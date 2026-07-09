import json
import subprocess
import sys
from pathlib import Path

FIX = Path("tests/fixtures/investment_memo")


def test_generate_memo_cli_smoke(tmp_path):
    out = tmp_path / "memo"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "generate-memo",
        "--audit-summary",
        str(FIX / "AAPL_audit_summary.json"),
        "--sensitivity",
        str(FIX / "AAPL_sensitivity_summary.json"),
        "--business-risk",
        str(FIX / "AAPL_business_risk_package.json"),
        "--thesis-status",
        str(FIX / "AAPL_thesis_status.json"),
        "--portfolio-audit",
        str(FIX / "core_portfolio_audit.json"),
        "--output",
        str(out),
    ]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "PASS_WITH_LIMITATIONS"
    assert payload["ticker"] == "AAPL"
    assert Path(payload["investment_memo_json"]).exists()
    assert Path(payload["investment_memo_md"]).exists()
    md = Path(payload["investment_memo_md"]).read_text(encoding="utf-8")
    assert "Not investment advice" in md
    assert "What remains UNKNOWN" in md
