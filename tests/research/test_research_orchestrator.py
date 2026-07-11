"""P2.1 orchestrator tests: full offline chain on the demo payload.

Everything runs offline on ``tests/fixtures/demo_complete_non_financial.json``
— the same fixture the manual chain e2e test uses — so the orchestrator's
behavior is directly comparable step for step with the hand-driven commands.
"""
import json
from pathlib import Path

import pytest
from jsonschema import validate

from sws_engine.research.orchestrator import (
    _count_unknown_checks,
    _source_step_status,
    run_research_company,
)

ROOT = Path(__file__).resolve().parents[2]
DEMO_PAYLOAD = ROOT / "tests" / "fixtures" / "demo_complete_non_financial.json"
SCHEMA = ROOT / "schemas" / "aux" / "research_company_run.schema.json"


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    # Config defaults (assumptions, dictionary, policies) resolve relative to
    # the repo root; artifacts stay inside tmp_path.
    monkeypatch.chdir(ROOT)
    return tmp_path


@pytest.fixture()
def chain(workdir):
    rep = run_research_company(
        db_path=str(workdir / "orc.db"),
        output_dir=workdir / "out",
        payload_path=str(DEMO_PAYLOAD),
    )
    return workdir, rep


def _steps(package):
    return {s["step_id"]: s for s in package["steps"]}


def test_full_chain_offline_statuses_and_schema(chain):
    workdir, rep = chain
    package = rep["package"]
    validate(instance=package,
             schema=json.loads(SCHEMA.read_text(encoding="utf-8")))

    steps = _steps(package)
    # Deterministic expectations on the demo payload: sensitivity is honestly
    # UNKNOWN (manual fair value) and must degrade the chain, never block it.
    assert steps["payload"]["status"] == "PASS"
    assert steps["engine"]["status"] == "PASS"
    assert steps["persist"]["status"] == "PASS"
    assert steps["audit"]["status"] == "PASS"
    assert steps["sensitivity"]["status"] == "UNKNOWN"
    assert steps["sensitivity"]["reason_code"] == \
        "SENSITIVITY_UNAVAILABLE_FOR_MANUAL_FAIR_VALUE"
    assert steps["explain"]["status"] == "PASS"
    assert steps["business_risk"]["status"] in {"PASS", "UNKNOWN"}
    assert steps["conflict_report"]["status"] in {"PASS", "UNKNOWN"}
    assert steps["memo"]["status"] == "PASS"

    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert package["reason_code"] == "RESEARCH_CHAIN_COMPLETE_WITH_LIMITATIONS"
    assert "sensitivity" in package["unknown_summary"]["unknown_steps"]
    assert package["run_id"], "persisted run_id must be carried in the report"
    assert package["mode"] == "offline_payload"
    # UNKNOWN preservation reaches the top-level report.
    assert package["unknown_summary"]["unknown_checks_count"] is not None


def test_artifacts_written_and_registered_in_index(chain):
    workdir, rep = chain
    package = rep["package"]
    db = str(workdir / "orc.db")
    tk = package["ticker"]

    run_json = Path(rep["paths"]["research_company_run_json"])
    run_md = Path(rep["paths"]["research_company_run_md"])
    assert run_json.exists() and run_md.exists()

    from sws_engine.db.artifacts import latest_artifact
    # The chain's own report is registered.
    assert latest_artifact(db, tk, "research_company_run_json")["path"] == str(run_json)
    # Every audit-chain artifact resolved through the P1.8 index.
    for kind in ("audit_summary_json", "sensitivity_summary_json",
                 "explanations_json", "business_risk_package_json",
                 "investment_memo_json"):
        found = latest_artifact(db, tk, kind)
        assert found and Path(found["path"]).exists(), f"missing in index: {kind}"

    # The memo auto-resolved from the index and its guardrails held.
    memo = json.loads(Path(latest_artifact(db, tk, "investment_memo_json")["path"])
                      .read_text(encoding="utf-8"))
    assert memo["recommendation_language_absent"] is True
    assert memo["sections"]["sensitivity_and_valuation_range"]["fragility_level"] == "UNKNOWN"


def test_report_md_has_no_recommendation_language(chain):
    workdir, rep = chain
    md = Path(rep["paths"]["research_company_run_md"]).read_text(encoding="utf-8")
    padded = f" {md} "
    for token in (" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "target price"):
        assert token not in padded
    assert "Not investment advice" in md
    # Per-step table is present with the honest UNKNOWN visible.
    assert "| Sensitivity / valuation range | UNKNOWN |" in md


def test_step_failure_is_isolated(workdir, monkeypatch):
    """A failing audit-chain step is recorded as FAIL and the rest still runs;
    the dependent memo step is honestly SKIPPED (audit summary unregistered)."""
    import sws_engine.audit.audit_report as ar

    def _boom(*a, **k):
        raise RuntimeError("forced audit failure")

    monkeypatch.setattr(ar, "audit_company_from_db_to_files", _boom)
    rep = run_research_company(
        db_path=str(workdir / "orc.db"),
        output_dir=workdir / "out",
        payload_path=str(DEMO_PAYLOAD),
    )
    package = rep["package"]
    steps = _steps(package)
    assert steps["audit"]["status"] == "FAIL"
    assert steps["audit"]["reason_code"] == "RESEARCH_CHAIN_STEP_FAILED"
    # Independent steps still ran.
    assert steps["sensitivity"]["status"] == "UNKNOWN"
    assert steps["business_risk"]["status"] in {"PASS", "UNKNOWN"}
    # Memo depends on the audit summary -> SKIPPED, not fabricated.
    assert steps["memo"]["status"] == "SKIPPED"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert "audit" in package["unknown_summary"]["failed_steps"]
    assert any("step 'audit' failed" in m for m in package["manual_review_items"])
    # Schema still holds on the degraded package.
    validate(instance=package,
             schema=json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_missing_payload_fails_fast_without_downstream(workdir):
    rep = run_research_company(
        db_path=str(workdir / "orc.db"),
        output_dir=workdir / "out",
        payload_path=str(workdir / "does_not_exist.json"),
    )
    package = rep["package"]
    steps = _steps(package)
    assert package["status"] == "FAIL"
    assert package["reason_code"] == "RESEARCH_CHAIN_INPUT_MISSING"
    assert steps["payload"]["status"] == "FAIL"
    for sid in ("engine", "persist", "audit", "sensitivity", "explain",
                "business_risk", "conflict_report", "memo"):
        assert steps[sid]["status"] == "SKIPPED"
    assert package["run_id"] is None
    validate(instance=package,
             schema=json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_mode_arguments_are_mutually_exclusive(workdir):
    with pytest.raises(ValueError):
        run_research_company(db_path=str(workdir / "x.db"),
                             output_dir=workdir / "out")
    with pytest.raises(ValueError):
        run_research_company(db_path=str(workdir / "x.db"),
                             output_dir=workdir / "out",
                             ticker="AAPL", payload_path=str(DEMO_PAYLOAD))


def test_offline_mode_documents_rates_injection_scope(chain):
    """Offline payloads carry their own rates; the report must say so
    explicitly instead of silently pretending an injection happened."""
    _, rep = chain
    inj = rep["package"]["injections"]
    assert inj["rates"]["reason_code"] == "RATES_INJECTION_NOT_APPLICABLE_OFFLINE"


def test_count_unknown_checks_uses_canonical_result_and_rejects_malformed_data():
    checks = ([{"result": "UNKNOWN"}] * 17
              + [{"result": "PASS"}] * 8
              + [{"result": "FAIL"}] * 5)
    assert _count_unknown_checks({"checks": checks}) == 17
    with pytest.raises(ValueError, match="canonical result"):
        _count_unknown_checks({"checks": [{"status": "UNKNOWN"}]})
    with pytest.raises(ValueError, match="must be a list"):
        _count_unknown_checks({})


@pytest.mark.parametrize(
    "status", ["PASS", "PASS_WITH_LIMITATIONS", "UNKNOWN", "FAIL"]
)
def test_source_step_status_preserves_all_canonical_mappings(status):
    assert _source_step_status(status) == status


def test_unknown_count_agrees_in_engine_detail_json_and_markdown(
    workdir, monkeypatch
):
    from sws_engine.orchestration.company_run import run_company_analysis

    payload = json.loads(DEMO_PAYLOAD.read_text(encoding="utf-8"))
    output = run_company_analysis(
        payload, "config/assumptions.yaml", "schemas/output_schema.json"
    )
    for index, check in enumerate(output["checks"]):
        if index < 17:
            check["result"] = "UNKNOWN"
            check["reason_code"] = "MISSING_INPUT"

    def _output_with_unknowns(*_args, **_kwargs):
        return output

    monkeypatch.setattr(
        "sws_engine.orchestration.company_run.run_company_analysis",
        _output_with_unknowns,
    )
    rep = run_research_company(
        db_path=str(workdir / "unknowns.db"),
        output_dir=workdir / "unknowns",
        payload_path=str(DEMO_PAYLOAD),
    )
    package = rep["package"]
    engine = _steps(package)["engine"]
    assert "unknown_checks=17" in engine["detail"]
    assert package["unknown_summary"]["unknown_checks_count"] == 17

    json_package = json.loads(
        Path(rep["paths"]["research_company_run_json"]).read_text(encoding="utf-8")
    )
    md = Path(rep["paths"]["research_company_run_md"]).read_text(encoding="utf-8")
    assert json_package["unknown_summary"]["unknown_checks_count"] == 17
    assert "UNKNOWN checks in engine output: 17" in md


def test_conflict_limitations_remain_visible_without_failed_step(
    workdir, monkeypatch
):
    def _limited_conflict_report(_payload, output_dir, **_kwargs):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "conflicts.json"
        md_path = output_dir / "conflicts.md"
        json_path.write_text("{}", encoding="utf-8")
        md_path.write_text("manual review required", encoding="utf-8")
        return {
            "report": {
                "status": "PASS_WITH_LIMITATIONS",
                "reason_code": "SOURCE_CONFLICT_MATERIAL_REVIEW_REQUIRED",
                "conflicts_count": 3,
                "material_count": 1,
                "unresolved_count": 0,
                "manual_review_required": True,
            },
            "paths": {
                "source_conflicts_json": str(json_path),
                "source_conflicts_report_md": str(md_path),
            },
        }

    monkeypatch.setattr(
        "sws_engine.sources.conflict_detector.write_conflict_report",
        _limited_conflict_report,
    )
    rep = run_research_company(
        db_path=str(workdir / "limited.db"),
        output_dir=workdir / "limited",
        payload_path=str(DEMO_PAYLOAD),
    )
    package = rep["package"]
    step = _steps(package)["conflict_report"]
    assert step["status"] == "PASS_WITH_LIMITATIONS"
    assert step["reason_code"] == "SOURCE_CONFLICT_MATERIAL_REVIEW_REQUIRED"
    assert package["status"] == "PASS_WITH_LIMITATIONS"
    assert "conflict_report" not in package["unknown_summary"]["failed_steps"]
    assert any(
        "conflict_report" in item
        and "SOURCE_CONFLICT_MATERIAL_REVIEW_REQUIRED" in item
        for item in package["manual_review_items"]
    )
    validate(
        instance=package,
        schema=json.loads(SCHEMA.read_text(encoding="utf-8")),
    )
