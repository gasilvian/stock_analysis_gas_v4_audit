import json
import subprocess
import sys


def test_refresh_rates_fred_cli(tmp_path):
    out = tmp_path / "rates.csv"
    report = tmp_path / "report.json"
    cmd = [
        sys.executable, "-m", "sws_engine.cli", "refresh-rates-fred",
        "--input-csv", "tests/fixtures/rates/fred_DGS10.csv",
        "--output", str(out),
        "--report", str(report),
    ]
    proc = subprocess.run(cmd, cwd=".", text=True, capture_output=True, env={"PYTHONPATH": "src"})
    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["observations_written"] == 3


def test_validate_erp_curated_cli(tmp_path):
    report = tmp_path / "erp_report.json"
    cmd = [
        sys.executable, "-m", "sws_engine.cli", "validate-erp-curated",
        "--input", "tests/fixtures/rates/erp_curated_reviewed.json",
        "--require-reviewed",
        "--output", str(report),
    ]
    proc = subprocess.run(cmd, cwd=".", text=True, capture_output=True, env={"PYTHONPATH": "src"})
    assert proc.returncode == 0, proc.stderr
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "PASS"


def test_enrich_identifiers_cli(tmp_path):
    out = tmp_path / "identifier_master.csv"
    report = tmp_path / "identifier_report.json"
    cmd = [
        sys.executable, "-m", "sws_engine.cli", "enrich-identifiers",
        "--input", "tests/fixtures/reference/universe_us_minimal.csv",
        "--cik-map", "tests/fixtures/reference/sec_company_tickers.json",
        "--output", str(out),
        "--report", str(report),
    ]
    proc = subprocess.run(cmd, cwd=".", text=True, capture_output=True, env={"PYTHONPATH": "src"})
    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["rows_written"] == 4
