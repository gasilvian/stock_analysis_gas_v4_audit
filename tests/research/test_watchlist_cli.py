import json
import subprocess
import sys
from pathlib import Path


def test_audit_watchlist_cli(tmp_path):
    out_dir = tmp_path / "watchlist"
    cmd = [
        sys.executable,
        "-m",
        "sws_engine.cli",
        "audit-watchlist",
        "--watchlist",
        "tests/fixtures/watchlist/watchlist.csv",
        "--audit-dir",
        "tests/fixtures/watchlist/audits",
        "--business-risk-dir",
        "tests/fixtures/watchlist/business_risks",
        "--output",
        str(out_dir),
    ]
    res = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["status"] == "PASS_WITH_LIMITATIONS"
    assert body["watchlist_size"] == 3
    assert Path(body["watchlist_audit_json"]).exists()
    assert Path(body["watchlist_audit_report_md"]).exists()
