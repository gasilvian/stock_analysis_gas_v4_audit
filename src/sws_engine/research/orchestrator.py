"""P2.1 research-company orchestrator: one command, the whole research chain.

Runs the full v4.0 research chain on a single company —

    payload (with every curated injection) -> engine -> persist -> audit
        -> sensitivity -> explain -> business-risk -> conflict-report -> memo

— producing a per-step report artifact (``research_company_run.json`` + a
Markdown rendering) and registering every produced artifact in the P1.8
SQLite artifact index so downstream consumers (memo ``--auto``, workflow
package, dashboard hub) resolve them without hand-wired paths.

Governance invariants (unchanged from the individual commands):

- UNKNOWN is preserved, never normalized away: a step that honestly returns
  UNKNOWN (e.g. sensitivity on a manual fair value) is recorded as UNKNOWN,
  degrades the chain to ``PASS_WITH_LIMITATIONS`` and never blocks the rest.
- No invented values: missing curated sources produce visible warnings and
  the affected fields stay MISSING in the payload.
- Step isolation: a failing audit-chain step is recorded as FAIL with its
  error and the remaining independent steps still run; only an engine or
  persistence failure aborts the chain (everything downstream depends on
  the persisted run).
- No recommendation language anywhere in the rendered report.

Two payload modes:

- ``payload_path`` (offline): a pre-built payload JSON is loaded as-is.
  Optional estimates/averages/SEC injections still apply (they are pure
  payload-level functions). Curated *rates* injection is live-mode only —
  it flows through the provider mapper — so in offline mode the payload is
  expected to already carry its rates (or honestly lack them).
- ``ticker`` (live): the yfinance pragmatic provider builds the payload with
  curated rates overrides, mirroring ``real-dashboard-bootstrap`` exactly,
  then estimates/averages/SEC injections apply on top.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

SCHEMA_VERSION = "research_company_run.v0.1"
SPRINT = "v4.0-p2.1"
NOT_INVESTMENT_ADVICE = (
    "Internal/personal/educational research audit artifact. "
    "Not investment advice. Contains no recommendation or rating language."
)

DEFAULT_ASSUMPTIONS = "config/assumptions.yaml"
DEFAULT_SCHEMA = "schemas/output_schema.json"

STEP_DEFINITIONS: List[Dict[str, str]] = [
    {"step_id": "payload", "label": "Payload with curated injections"},
    {"step_id": "engine", "label": "v3.1 engine run (schema-valid output)"},
    {"step_id": "persist", "label": "SQLite persistence (input snapshot + run + output)"},
    {"step_id": "audit", "label": "Audit layer (data confidence, applicability, conclusion risk)"},
    {"step_id": "sensitivity", "label": "Sensitivity / valuation range"},
    {"step_id": "explain", "label": "Deterministic reason-code explanations"},
    {"step_id": "business_risk", "label": "Red flags, accounting quality, capital allocation"},
    {"step_id": "conflict_report", "label": "Source conflict report"},
    {"step_id": "memo", "label": "Investment research audit memo (artifact-index auto)"},
]

_FORBIDDEN_TOKENS = (" BUY ", " SELL ", " HOLD ", "BUY/SELL/HOLD", "target price")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _provider(refresh: bool = False):
    """Live provider factory; monkeypatched in offline tests (mirrors
    ``ops.real_dashboard_bootstrap._provider``)."""
    from sws_engine.providers.yfinance_live import YFinanceLiveProvider
    return YFinanceLiveProvider(refresh=refresh)


def _step(step_id: str, label: str) -> Dict[str, Any]:
    return {
        "step_id": step_id,
        "label": label,
        "status": "SKIPPED",
        "reason_code": "RESEARCH_CHAIN_STEP_SKIPPED",
        "detail": None,
        "artifacts": {},
        "duration_ms": None,
    }


def _finish(step: Dict[str, Any], started: float, status: str, reason_code: str,
            detail: Optional[str] = None, artifacts: Optional[Mapping[str, str]] = None) -> None:
    step["status"] = status
    step["reason_code"] = reason_code
    step["detail"] = detail
    if artifacts:
        step["artifacts"] = dict(artifacts)
    step["duration_ms"] = int((time.monotonic() - started) * 1000)


def _register(db_path: str, ticker: str, paths: Mapping[str, str],
              run_id: Optional[str]) -> None:
    from sws_engine.db.artifacts import register_paths
    register_paths(db_path, ticker=ticker, paths=dict(paths), run_id=run_id)


def _count_unknown_checks(output: Mapping[str, Any]) -> int:
    return sum(1 for c in (output.get("checks") or []) if c.get("status") == "UNKNOWN")


def run_research_company(
    *,
    db_path: str,
    output_dir: str | Path,
    ticker: Optional[str] = None,
    payload_path: Optional[str] = None,
    market: str = "US",
    valuation_date: str = "auto",
    assumptions_path: str = DEFAULT_ASSUMPTIONS,
    schema_path: str = DEFAULT_SCHEMA,
    bond_csv: Optional[str] = None,
    erp_json: Optional[str] = None,
    sec_dir: Optional[str] = None,
    averages_json: Optional[str] = None,
    estimates_dir: Optional[str] = None,
    memo_type: str = "company",
    explain_mode: str = "analyst",
    material_threshold: float = 0.05,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Run the full research chain; return {"package": ..., "paths": ...}.

    Exactly one of ``payload_path`` (offline) / ``ticker`` (live) selects the
    payload mode. ``db_path`` is mandatory: the chain is defined over a
    persisted run plus the artifact index.
    """
    if bool(payload_path) == bool(ticker):
        raise ValueError(
            "exactly one of payload_path (offline) or ticker (live) is required")
    if not db_path:
        raise ValueError("db_path is required: the research chain is defined "
                         "over a persisted run and the artifact index")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mode = "offline_payload" if payload_path else "live"
    vdate = None if (valuation_date or "auto") == "auto" else valuation_date

    steps = {d["step_id"]: _step(d["step_id"], d["label"]) for d in STEP_DEFINITIONS}
    warnings: List[str] = []
    injections: Dict[str, Any] = {}
    payload: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    resolved_ticker: Optional[str] = ticker

    # ---- 1. payload ------------------------------------------------------
    t0 = time.monotonic()
    try:
        if payload_path:
            if not os.path.exists(payload_path):
                raise FileNotFoundError(f"payload file not found: {payload_path}")
            with open(payload_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            injections["rates"] = {
                "reason_code": "RATES_INJECTION_NOT_APPLICABLE_OFFLINE",
                "detail": "offline payload mode: curated rates flow through the "
                          "provider mapper and only apply in live mode; the "
                          "payload is used as provided",
            }
        else:
            from sws_engine.rates.injection import build_curated_rates_overrides
            rates_overrides = None
            if bond_csv or erp_json:
                rj = build_curated_rates_overrides(
                    bond_csv or "", erp_json or "", country=market or "US",
                    valuation_date=vdate or date.today().isoformat())
                rates_overrides = rj["overrides"] or None
                warnings.extend(rj["warnings"])
                injections["rates"] = {
                    "applied_fields": sorted((rj["overrides"] or {}).keys()),
                    "warnings_count": len(rj["warnings"]),
                }
            provider = _provider(refresh=refresh)
            payload = provider.build_payload(
                ticker, valuation_date=vdate, market=market, industry=None,
                overrides=rates_overrides)

        if estimates_dir:
            from sws_engine.estimates.manual_pack import apply_estimates_from_dir
            est = apply_estimates_from_dir(
                payload, estimates_dir,
                valuation_date=vdate or date.today().isoformat())
            injections["estimates"] = {
                "reason_code": est["reason_code"],
                "applied_fields": est["applied_fields"],
            }
        if averages_json:
            from sws_engine.averages.injection import (apply_averages_snapshot,
                                                       load_averages_snapshot)
            if os.path.exists(averages_json):
                avg = apply_averages_snapshot(payload, load_averages_snapshot(averages_json))
                injections["averages"] = {
                    "reason_code": avg["reason_code"],
                    "applied_fields": avg["applied_fields"],
                    "industry_matched": avg["industry_matched"],
                }
            else:
                warnings.append(
                    f"CURATED_AVERAGES_FILE_MISSING: '{averages_json}' not found; "
                    "market/industry averages stay MISSING")
        if sec_dir:
            from sws_engine.sec.payload_merge import merge_sec_updates_from_dir
            sec = merge_sec_updates_from_dir(payload, sec_dir)
            injections["sec"] = {
                "reason_code": sec["reason_code"],
                "applied_fields_count": len(sec["applied_fields"]),
                "conflicts_count": len(sec["conflicts"]),
            }

        resolved_ticker = str(payload.get("ticker") or resolved_ticker or "UNKNOWN")
        p_path = str(out_dir / f"{resolved_ticker}_payload.json")
        with open(p_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        _finish(steps["payload"], t0, "PASS", "RESEARCH_CHAIN_STEP_OK",
                detail=f"mode={mode}; injections={sorted(injections.keys()) or 'none'}",
                artifacts={"research_payload_json": p_path})
    except Exception as exc:
        _finish(steps["payload"], t0, "FAIL", "RESEARCH_CHAIN_INPUT_MISSING",
                detail=f"{exc.__class__.__name__}: {exc}")
        return _finalize(steps, out_dir, db_path=db_path, ticker=resolved_ticker,
                         run_id=None, mode=mode, output=None,
                         warnings=warnings, injections=injections)

    # ---- 2. engine -------------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.orchestration.company_run import run_company_analysis
        output = run_company_analysis(payload, assumptions_path, schema_path)
        resolved_ticker = str(output["ticker"])
        o_path = str(out_dir / f"{resolved_ticker}_output.json")
        with open(o_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2)
        _finish(steps["engine"], t0, "PASS", "RESEARCH_CHAIN_STEP_OK",
                detail=f"unknown_checks={_count_unknown_checks(output)}; "
                       f"provider_profile={output.get('provider_profile')}",
                artifacts={"research_engine_output_json": o_path})
    except Exception as exc:
        _finish(steps["engine"], t0, "FAIL", "RESEARCH_CHAIN_ENGINE_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")
        return _finalize(steps, out_dir, db_path=db_path, ticker=resolved_ticker,
                         run_id=None, mode=mode, output=None,
                         warnings=warnings, injections=injections)

    # ---- 3. persist ------------------------------------------------------
    t0 = time.monotonic()
    try:
        import sws_engine as _pkg
        from sws_engine.db.store import Store, assumptions_hash
        store = Store(db_path)
        store.init_schema()
        store.upsert_instrument(ticker=output["ticker"])
        snapshot_id = store.save_input_snapshot(output["ticker"], payload)
        run_id = store.create_run(
            ticker=output["ticker"], valuation_date=output.get("valuation_date"),
            snapshot_id=snapshot_id,
            assumptions_hash=assumptions_hash(assumptions_path),
            engine_version=getattr(_pkg, "__version__", "unknown"),
            status="PASS")
        store.save_output(run_id, output)
        store.close()
        _finish(steps["persist"], t0, "PASS", "RESEARCH_CHAIN_STEP_OK",
                detail=f"run_id={run_id}")
    except Exception as exc:
        _finish(steps["persist"], t0, "FAIL", "RESEARCH_CHAIN_PERSIST_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")
        return _finalize(steps, out_dir, db_path=db_path, ticker=resolved_ticker,
                         run_id=None, mode=mode, output=output,
                         warnings=warnings, injections=injections)

    tk = resolved_ticker

    # ---- 4. audit --------------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.audit.audit_report import audit_company_from_db_to_files
        rep = audit_company_from_db_to_files(db_path, tk, out_dir / "audit",
                                             run_id=run_id)
        _register(db_path, tk, rep["paths"], run_id)
        s = rep["summary"]
        _finish(steps["audit"], t0, "PASS", "RESEARCH_CHAIN_STEP_OK",
                detail=(f"data_confidence={s.get('data_confidence', {}).get('level')}; "
                        f"model_applicability={s.get('model_applicability', {}).get('status')}; "
                        f"conclusion_risk={s.get('conclusion_risk', {}).get('risk_level')}"),
                artifacts=rep["paths"])
    except Exception as exc:
        _finish(steps["audit"], t0, "FAIL", "RESEARCH_CHAIN_STEP_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")

    # ---- 5. sensitivity ---------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.sensitivity.report import sensitivity_company_to_files
        rep = sensitivity_company_to_files(out_dir / "sensitivity",
                                           db_path=db_path, ticker=tk, run_id=run_id,
                                           assumptions_path=assumptions_path)
        _register(db_path, tk, rep["paths"], run_id)
        s = rep["summary"]
        status = "UNKNOWN" if s.get("status") == "UNKNOWN" else "PASS"
        _finish(steps["sensitivity"], t0, status,
                s.get("reason_code") or "RESEARCH_CHAIN_STEP_OK",
                detail=f"fragility={(s.get('fragility') or {}).get('fragility_level')}",
                artifacts=rep["paths"])
    except Exception as exc:
        _finish(steps["sensitivity"], t0, "FAIL", "RESEARCH_CHAIN_STEP_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")

    # ---- 6. explain --------------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.audit.audit_summary import (build_audit_summary,
                                                    load_latest_audit_context_from_db)
        from sws_engine.explain.check_explainer import (build_explanation_package,
                                                        write_explanation_artifacts)
        ctx = load_latest_audit_context_from_db(db_path, tk, run_id=run_id)
        summary = build_audit_summary(
            ctx["output"], run_id=ctx["run_id"],
            input_payload=ctx.get("input_payload"),
            assumptions_hash=ctx.get("assumptions_hash"),
            engine_version=ctx.get("engine_version"))
        package = build_explanation_package(ctx["output"], audit_summary=summary,
                                            mode=explain_mode)
        paths = write_explanation_artifacts(package, out_dir / "explain")
        _register(db_path, tk, paths, run_id)
        _finish(steps["explain"], t0, "PASS", "RESEARCH_CHAIN_STEP_OK",
                detail=(f"explained={package.get('checks_explained_count')}; "
                        f"unknown={package.get('unknown_checks_count')}"),
                artifacts=paths)
    except Exception as exc:
        _finish(steps["explain"], t0, "FAIL", "RESEARCH_CHAIN_STEP_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")

    # ---- 7. business risk ---------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.audit.risk_signals import business_risk_company_to_files
        rep = business_risk_company_to_files(out_dir / "business_risk",
                                             db_path=db_path, ticker=tk, run_id=run_id)
        _register(db_path, tk, rep["paths"], run_id)
        pk = rep["package"]
        status = "UNKNOWN" if pk.get("status") == "UNKNOWN" else "PASS"
        _finish(steps["business_risk"], t0, status,
                pk.get("reason_code") or "RESEARCH_CHAIN_STEP_OK",
                detail=(f"red_flags_fail={pk.get('red_flags_summary', {}).get('fail_count')}; "
                        f"accounting_grade={pk.get('accounting_quality', {}).get('grade')}"),
                artifacts=rep["paths"])
    except Exception as exc:
        _finish(steps["business_risk"], t0, "FAIL", "RESEARCH_CHAIN_STEP_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")

    # ---- 8. conflict report --------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.sources.conflict_detector import write_conflict_report
        rep = write_conflict_report(payload, out_dir / "conflicts",
                                    material_threshold=material_threshold)
        _register(db_path, tk, rep["paths"], run_id)
        r = rep["report"]
        status = "PASS" if r["status"] == "PASS" else (
            "UNKNOWN" if r["status"] == "UNKNOWN" else "FAIL")
        _finish(steps["conflict_report"], t0, status,
                r.get("reason_code") or "RESEARCH_CHAIN_STEP_OK",
                detail=(f"conflicts={r.get('conflicts_count')}; "
                        f"material={r.get('material_count')}; "
                        f"unresolved={r.get('unresolved_count')}"),
                artifacts=rep["paths"])
    except Exception as exc:
        _finish(steps["conflict_report"], t0, "FAIL", "RESEARCH_CHAIN_STEP_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")

    # ---- 9. memo ---------------------------------------------------------------
    t0 = time.monotonic()
    try:
        from sws_engine.db.artifacts import latest_artifact
        wanted = {
            "audit_summary_path": "audit_summary_json",
            "explanations_path": "explanations_json",
            "sensitivity_path": "sensitivity_summary_json",
            "business_risk_path": "business_risk_package_json",
            "thesis_status_path": "thesis_status_json",
            "decision_record_path": "decision_record_json",
            "portfolio_audit_path": "portfolio_audit_json",
        }
        resolved: Dict[str, Optional[str]] = {}
        for kw, kind in wanted.items():
            found = latest_artifact(db_path, tk, kind)
            resolved[kw] = found["path"] if found else None
        if not resolved["audit_summary_path"]:
            _finish(steps["memo"], t0, "SKIPPED", "RESEARCH_CHAIN_STEP_SKIPPED",
                    detail="no audit_summary in the artifact index (audit step "
                           "failed); memo requires it and stays unproduced")
        else:
            from sws_engine.reporting.investment_memo import investment_memo_to_files
            rep = investment_memo_to_files(out_dir / "memo",
                                           memo_type=memo_type, **resolved)
            _register(db_path, tk, rep["paths"], run_id)
            pk = rep["package"]
            status = "PASS" if pk.get("status") != "FAIL" else "FAIL"
            _finish(steps["memo"], t0, status,
                    pk.get("reason_code") or "RESEARCH_CHAIN_STEP_OK",
                    detail=(f"manual_review_items={len(pk.get('manual_review_items') or [])}; "
                            "recommendation_language_absent="
                            f"{pk.get('recommendation_language_absent')}"),
                    artifacts=rep["paths"])
    except Exception as exc:
        _finish(steps["memo"], t0, "FAIL", "RESEARCH_CHAIN_STEP_FAILED",
                detail=f"{exc.__class__.__name__}: {exc}")

    return _finalize(steps, out_dir, db_path=db_path, ticker=tk, run_id=run_id,
                     mode=mode, output=output, warnings=warnings,
                     injections=injections)


def _finalize(steps: Dict[str, Dict[str, Any]], out_dir: Path, *, db_path: str,
              ticker: Optional[str], run_id: Optional[str], mode: str,
              output: Optional[Mapping[str, Any]], warnings: List[str],
              injections: Mapping[str, Any]) -> Dict[str, Any]:
    ordered = [steps[d["step_id"]] for d in STEP_DEFINITIONS]
    statuses = [s["status"] for s in ordered]

    if steps["engine"]["status"] == "FAIL" or steps["persist"]["status"] == "FAIL" \
            or steps["payload"]["status"] == "FAIL":
        overall, reason = "FAIL", (
            "RESEARCH_CHAIN_ENGINE_FAILED" if steps["engine"]["status"] == "FAIL"
            else "RESEARCH_CHAIN_PERSIST_FAILED" if steps["persist"]["status"] == "FAIL"
            else "RESEARCH_CHAIN_INPUT_MISSING")
    elif any(s in ("FAIL", "UNKNOWN", "SKIPPED") for s in statuses) or warnings:
        overall, reason = "PASS_WITH_LIMITATIONS", "RESEARCH_CHAIN_COMPLETE_WITH_LIMITATIONS"
    else:
        overall, reason = "PASS", "RESEARCH_CHAIN_COMPLETE"

    unknown_steps = [s["step_id"] for s in ordered if s["status"] == "UNKNOWN"]
    failed_steps = [s["step_id"] for s in ordered if s["status"] == "FAIL"]
    skipped_steps = [s["step_id"] for s in ordered if s["status"] == "SKIPPED"]
    manual_review: List[str] = []
    for sid in unknown_steps:
        manual_review.append(
            f"step '{sid}' is honestly UNKNOWN ({steps[sid]['reason_code']}): "
            f"{steps[sid]['detail']}")
    for sid in failed_steps:
        manual_review.append(f"step '{sid}' failed: {steps[sid]['detail']}")
    for sid in skipped_steps:
        manual_review.append(f"step '{sid}' skipped: {steps[sid]['detail'] or 'dependency unavailable'}")
    for w in warnings:
        manual_review.append(f"payload warning: {w}")

    package: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "sprint": SPRINT,
        "status": overall,
        "reason_code": reason,
        "ticker": ticker or "UNKNOWN",
        "run_id": run_id,
        "mode": mode,
        "generated_at": _utc_now(),
        "steps": ordered,
        "injections": dict(injections),
        "payload_warnings": list(warnings),
        "unknown_summary": {
            "unknown_steps": unknown_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "unknown_checks_count": _count_unknown_checks(output) if output else None,
        },
        "manual_review_items": manual_review,
        "recommendation_language_absent": True,
        "not_investment_advice": NOT_INVESTMENT_ADVICE,
    }

    md = render_research_run_report_md(package)
    padded = f" {md} "
    for token in _FORBIDDEN_TOKENS:
        if token in padded:
            raise ValueError(f"recommendation language detected in report: {token!r}")

    tk = package["ticker"]
    json_path = out_dir / f"{tk}_research_company_run.json"
    md_path = out_dir / f"{tk}_research_company_run.md"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(package, fh, indent=2)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    paths = {"research_company_run_json": str(json_path),
             "research_company_run_md": str(md_path)}
    try:
        _register(db_path, tk, paths, run_id)
    except Exception:
        pass  # the report on disk is authoritative; index registration is best-effort
    return {"package": package, "paths": paths}


def render_research_run_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        f"# Research Company Run — {package['ticker']}",
        "",
        f"- Status: **{package['status']}** ({package['reason_code']})",
        f"- Run ID: `{package.get('run_id') or 'UNKNOWN'}`",
        f"- Mode: {package.get('mode')}",
        f"- Generated at: {package.get('generated_at')}",
        "",
        "## Steps",
        "",
        "| Step | Status | Reason code | Detail |",
        "|---|---|---|---|",
    ]
    for s in package["steps"]:
        detail = (s.get("detail") or "").replace("|", "\\|")
        lines.append(f"| {s['label']} | {s['status']} | {s['reason_code']} | {detail} |")
    inj = package.get("injections") or {}
    lines += ["", "## Injections", ""]
    if inj:
        for name, rep in inj.items():
            lines.append(f"- **{name}**: {json.dumps(rep, ensure_ascii=False)}")
    else:
        lines.append("- none requested")
    pw = package.get("payload_warnings") or []
    if pw:
        lines += ["", "## Payload warnings", ""]
        lines += [f"- {w}" for w in pw]
    mri = package.get("manual_review_items") or []
    lines += ["", "## Manual review items", ""]
    lines += ([f"- {m}" for m in mri] if mri else ["- none"])
    us = package.get("unknown_summary") or {}
    lines += [
        "",
        "## UNKNOWN summary",
        "",
        f"- UNKNOWN steps: {', '.join(us.get('unknown_steps') or []) or 'none'}",
        f"- Failed steps: {', '.join(us.get('failed_steps') or []) or 'none'}",
        f"- Skipped steps: {', '.join(us.get('skipped_steps') or []) or 'none'}",
        f"- UNKNOWN checks in engine output: {us.get('unknown_checks_count')}",
        "",
        "---",
        "",
        f"*{package['not_investment_advice']}*",
        "",
    ]
    return "\n".join(lines)
