import json
import subprocess
import sys
from pathlib import Path

from jsonschema import validate

from sws_engine.api.db_adapter import ApiDbAdapter
from sws_engine.audit.audit_report import audit_report_md, write_audit_artifacts
from sws_engine.audit.audit_summary import build_audit_summary


def _output():
    return json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))


def test_audit_summary_preserves_unknown_and_schema_valid():
    out = _output()
    out["checks"][0]["result"] = "UNKNOWN"
    out["checks"][0]["reason_code"] = "MISSING_FCF_ESTIMATES"
    out["checks"][0]["source_quality"] = "missing"
    summary = build_audit_summary(out, input_payload={"company_type": "non_financial"}, run_id="run-1")
    assert summary["data_confidence"]["unknown_checks_count"] == 1
    assert summary["unknown_clusters"]
    schema = json.loads(Path("schemas/aux/audit_summary.schema.json").read_text(encoding="utf-8"))
    validate(summary, schema)


def test_audit_report_contains_warnings_lineage_and_unknown():
    out = _output()
    out["checks"][0]["result"] = "UNKNOWN"
    out["checks"][0]["reason_code"] = "MISSING_FCF_ESTIMATES"
    out["checks"][0]["source_quality"] = "missing"
    summary = build_audit_summary(out, input_payload={"company_type": "non_financial"}, run_id="run-1")
    md = audit_report_md(summary)
    assert "What we don't know" in md
    assert "UNKNOWN" in md
    assert "Assumptions hash" in md
    assert "Not investment advice" in md


def test_write_audit_artifacts(tmp_path):
    summary = build_audit_summary(_output(), input_payload={"company_type": "non_financial"}, run_id="run-1")
    paths = write_audit_artifacts(summary, tmp_path)
    assert Path(paths["audit_summary_json"]).exists()
    assert Path(paths["audit_report_md"]).exists()


def test_audit_company_cli(tmp_path):
    db_path = tmp_path / "sws.db"
    adapter = ApiDbAdapter(str(db_path), "config/assumptions.yaml")
    out = _output()
    run_id = adapter.save_company_output(out, {"ticker": out["ticker"], "provider_profile": out["provider_profile"], "company_type": "non_financial"})
    adapter.close()

    out_dir = tmp_path / "audit"
    proc = subprocess.run(
        [sys.executable, "-m", "sws_engine.cli", "audit-company", "--ticker", out["ticker"], "--db", str(db_path), "--output", str(out_dir)],
        check=False,
        text=True,
        capture_output=True,
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["run_id"] == run_id
    assert Path(payload["audit_summary_json"]).exists()
    assert Path(payload["audit_report_md"]).exists()
