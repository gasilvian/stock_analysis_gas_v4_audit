import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run(args):
    return subprocess.run([sys.executable, "-m", "sws_engine.cli"] + args,
                          cwd=ROOT, capture_output=True, text=True)


def test_cli_company_and_portfolio(tmp_path):
    out = tmp_path / "c.json"
    rep = tmp_path / "c.md"
    r = _run(["company", "-i", "tests/fixtures/demo_complete_non_financial.json",
              "-o", str(out), "--report", str(rep)])
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text())
    assert len([c for c in data["checks"] if c["axis"] != "management"]) == 30
    assert "# Snowflake Report" in rep.read_text()

    pout = tmp_path / "p.json"
    prep = tmp_path / "p.md"
    r = _run(["portfolio", "-i", "tests/fixtures/demo_portfolio.json",
              "-o", str(pout), "--report", str(prep)])
    assert r.returncode == 0, r.stderr
    pdata = json.loads(pout.read_text())
    amzn = pdata["returns_per_position"]["AMZN"]
    assert abs(amzn["total_return"] - 1.0015) < 0.001
    assert "Portfolio Snowflake" in prep.read_text()
