import json
from pathlib import Path

from jsonschema import validate

from sws_engine.release.manifest import (
    build_release_manifest,
    release_to_files,
    render_release_report_md,
    write_release_artifacts,
)

SCHEMA = Path("schemas/aux/release_manifest.schema.json")


def test_release_manifest_schema_and_mvp_limitations():
    manifest = build_release_manifest(repo_root=".", release_id="test-release")
    validate(instance=manifest, schema=json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert manifest["schema_version"] == "release_manifest.v0.1"
    assert manifest["sprint"] == "v4.0-p0.14"
    assert manifest["status"] == "MVP_COMPLETE_WITH_LIMITATIONS"
    assert manifest["reason_code"] == "RELEASE_MVP_COMPLETE_WITH_LIMITATIONS"
    assert manifest["scope_guardrails"]["production_readiness"] == "NOT_READY"
    assert manifest["scope_guardrails"]["not_investment_advice"] is True
    assert manifest["scope_guardrails"]["unknown_policy_preserved"] is True
    assert manifest["capability_summary"]["unknown_or_missing"] == 0
    assert any(item["reason_code"] == "RELEASE_PRODUCTION_NOT_READY" for item in manifest["manual_review_items"])


def test_release_report_contains_guardrails(tmp_path):
    manifest = build_release_manifest(repo_root=".", release_id="test-release")
    paths = write_release_artifacts(manifest, tmp_path)
    report = Path(paths["release_report_md"]).read_text(encoding="utf-8")
    obj = json.loads(Path(paths["release_manifest_json"]).read_text(encoding="utf-8"))
    assert obj["not_investment_advice"] is True
    assert "What remains UNKNOWN or limited" in report
    assert "Not investment advice" in report
    assert "MVP_COMPLETE_WITH_LIMITATIONS" in report
    assert "BUY" not in report
    assert "SELL" not in report
    assert "Release Closure" in render_release_report_md(manifest)


def test_release_to_files_smoke(tmp_path):
    rep = release_to_files(tmp_path, repo_root=".", release_id="test-release")
    assert rep["manifest"]["release_id"] == "test-release"
    assert Path(rep["paths"]["release_manifest_json"]).exists()
    assert Path(rep["paths"]["release_report_md"]).exists()
