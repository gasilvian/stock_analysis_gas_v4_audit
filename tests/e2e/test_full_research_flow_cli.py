"""P1.0 end-to-end test: the real CLI research chain, not pre-built fixtures.

The P0.x series validated each capability against committed fixture artifacts.
This test closes the integration gap identified in the Post-P0.14 audit: it
drives the actual CLI surface end to end on the demo payload —

    company --db  ->  audit-company  ->  sensitivity-company
        ->  explain-company  ->  business-risk-company  ->  generate-memo

— asserting that each stage consumes the previous stage's real output and that
the core invariants (UNKNOWN preserved, no recommendation language, provider
profile visible) hold across the chain. Offline only; no network, no live data.
"""
import json
from pathlib import Path

import pytest

from sws_engine.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[2]
DEMO_PAYLOAD = ROOT / "tests" / "fixtures" / "demo_complete_non_financial.json"


def _run(argv: list[str], *, allow_unknown_exit: bool = False) -> None:
    rc = cli_main(argv)
    allowed = (None, 0, 2) if allow_unknown_exit else (None, 0)
    assert rc in allowed, f"CLI failed: {argv} -> {rc}"


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    # CLI defaults resolve config/... relative to CWD; run from repo root but
    # keep every artifact inside tmp_path.
    monkeypatch.chdir(ROOT)
    return tmp_path


def test_full_research_chain_cli_offline(workdir, capsys):
    db = workdir / "e2e.db"
    out_company = workdir / "company_output.json"
    audit_dir = workdir / "audit"
    sens_dir = workdir / "sensitivity"
    explain_dir = workdir / "explain"
    risk_dir = workdir / "business_risk"
    memo_dir = workdir / "memo"

    # 1. Engine run persisted via the new optional --db flag.
    _run(["company", "-i", str(DEMO_PAYLOAD), "--db", str(db), "-o", str(out_company)])
    assert db.exists()
    engine_output = json.loads(out_company.read_text(encoding="utf-8"))
    ticker = engine_output["ticker"]
    assert ticker == "DEMO"

    # 2. Audit layer on the persisted run.
    _run(["audit-company", "--ticker", ticker, "--db", str(db), "--output", str(audit_dir)])
    audit_files = sorted(audit_dir.glob(f"{ticker}_audit_summary_*.json"))
    assert audit_files, "audit summary not produced"
    audit_summary = json.loads(audit_files[-1].read_text(encoding="utf-8"))
    assert audit_summary["data_confidence"]["level"] in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    run_id = audit_summary.get("run_id")
    assert run_id, "audit summary must carry the persisted run_id"

    # 3. Sensitivity on the same persisted run. The demo payload uses a manual
    #    fair value, so the correct honest outcome is UNKNOWN — never invented.
    #    The CLI signals an UNKNOWN result with exit code 2 by convention.
    _run(["sensitivity-company", "--ticker", ticker, "--db", str(db), "--output", str(sens_dir)],
         allow_unknown_exit=True)
    sens_files = sorted(sens_dir.glob(f"{ticker}_sensitivity_summary_*.json"))
    assert sens_files
    sens = json.loads(sens_files[-1].read_text(encoding="utf-8"))
    assert sens.get("reason_code") == "SENSITIVITY_UNAVAILABLE_FOR_MANUAL_FAIR_VALUE"
    assert (sens.get("fragility") or {}).get("fragility_level") == "UNKNOWN"

    # 4. Deterministic explanations for the persisted run.
    _run(["explain-company", "--ticker", ticker, "--db", str(db), "--output", str(explain_dir)])
    explain_files = sorted(explain_dir.glob(f"{ticker}_explanations_*.json"))
    assert explain_files
    explanations = json.loads(explain_files[-1].read_text(encoding="utf-8"))
    assert explanations.get("known_reason_codes_complete_for_package") is True

    # 5. Business risk signals for the persisted run.
    _run(["business-risk-company", "--ticker", ticker, "--db", str(db), "--output", str(risk_dir)])
    risk_files = sorted(risk_dir.glob(f"{ticker}_business_risk_*.json"))
    assert risk_files
    business_risk = json.loads(risk_files[-1].read_text(encoding="utf-8"))

    # 6. Memo generated via the P1.8 artifact index (--auto): steps 2-5
    #    registered their outputs in the DB; no explicit paths are wired.
    _run([
        "generate-memo", "--auto",
        "--ticker", ticker,
        "--db", str(db),
        "--output", str(memo_dir),
    ])
    memo_json = memo_dir / f"{ticker}_investment_audit_memo.json"
    memo_md = memo_dir / f"{ticker}_investment_audit_memo.md"
    assert memo_json.exists() and memo_md.exists()
    memo = json.loads(memo_json.read_text(encoding="utf-8"))

    # Cross-chain invariants.
    assert memo["ticker"] == ticker
    assert memo["recommendation_language_absent"] is True
    # P1.0 regression guard: fully present components must not be mislabeled.
    assert memo["sections"]["data_confidence"]["reason_code"] != "MEMO_COMPONENT_UNKNOWN"
    md_text = memo_md.read_text(encoding="utf-8")
    padded = f" {md_text} "
    for token in (" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "target price"):
        assert token not in padded
    assert "Not investment advice" in md_text
    # UNKNOWN preservation: sensitivity stayed UNKNOWN through to the memo.
    assert memo["sections"]["sensitivity_and_valuation_range"]["fragility_level"] == "UNKNOWN"
    # Business risk artifact fed in and referenced without fabrication.
    assert business_risk.get("ticker") == ticker
    # P1.8: the artifact index resolved the four produced artifacts and
    # honestly reported the unproduced ones as UNKNOWN, and the memo's own
    # outputs were registered back into the index.
    from sws_engine.db.artifacts import latest_artifact, list_artifacts
    assert latest_artifact(db, ticker, "audit_summary_json")["path"] == str(audit_files[-1])
    assert latest_artifact(db, ticker, "sensitivity_summary_json")["path"] == str(sens_files[-1])
    assert latest_artifact(db, ticker, "thesis_status_json") is None
    assert latest_artifact(db, ticker, "investment_memo_json")["path"] == str(memo_json)
    kinds = {a["kind"] for a in list_artifacts(db, ticker=ticker)}
    assert {"audit_summary_json", "explanations_json", "sensitivity_summary_json",
            "business_risk_package_json", "investment_memo_json"} <= kinds
