"""Real-data dashboard bootstrap (provider_profile=yfinance_pragmatic).

Operational-only module. It wires the existing yfinance live provider ->
run_company_analysis -> SQLite persistence for a small real universe so the
dashboard can display real tickers.

Hard rules enforced here (mirroring the model pack):
- no model logic, no check logic, no schema changes;
- missing analytical inputs are NOT invented: they stay missing and the
  engine produces UNKNOWN + warnings + degraded source_quality;
- missing curated rates/ERP sources produce visible warnings
  (MISSING_CURATED_RATE_SOURCE / MISSING_CURATED_ERP_SOURCE) and never
  crash the batch;
- a failed ticker never stops the batch (error isolation).
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_ASSUMPTIONS = "config/assumptions.yaml"
DEFAULT_SCHEMA = "schemas/output_schema.json"
DEFAULT_OUTPUT_DIR = "out/real_dashboard_bootstrap"
DEFAULT_DB = "data/sws.db"
DEFAULT_BOND_CURATED = "data/real_sources/rates/bond_yields_10y_curated.csv"
DEFAULT_ERP_CURATED = "data/real_sources/rates/erp_curated.json"

WARN_MISSING_RATES = "MISSING_CURATED_RATE_SOURCE"
WARN_MISSING_ERP = "MISSING_CURATED_ERP_SOURCE"

FOOTER = (
    "Internal, non-commercial, educational use only. Not investment advice. "
    "Not the live Simply Wall St model. Methodology attribution: Simply Wall St "
    "public Company-Analysis-Model / Portfolio-Analysis-Model repositories "
    "(CC BY-NC-SA 4.0)."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _provider(refresh: bool = False):
    """Provider factory; monkeypatched in offline tests."""
    from sws_engine.providers.yfinance_live import YFinanceLiveProvider
    return YFinanceLiveProvider(refresh=refresh)


def _read_watchlist(path: str) -> List[str]:
    tickers: List[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            cell = line.strip().split(",")[0].strip()
            if not cell or cell.lower() == "ticker":
                continue
            tickers.append(cell)
    return tickers


def _resolve_tickers(tickers: Optional[str | List[str]], watchlist_path: Optional[str]) -> List[str]:
    if tickers:
        if isinstance(tickers, str):
            items = [t.strip() for t in tickers.split(",") if t.strip()]
        else:
            items = [str(t).strip() for t in tickers if str(t).strip()]
        if items:
            return items
    if watchlist_path:
        return _read_watchlist(watchlist_path)
    raise ValueError("real-dashboard-bootstrap requires --tickers or --watchlist")


def _curated_source_warnings(bond_csv: str, erp_json: str) -> List[str]:
    warnings: List[str] = []
    if not os.path.exists(bond_csv):
        warnings.append(
            f"{WARN_MISSING_RATES}: '{bond_csv}' not found; discount-rate dependent "
            "checks may be UNKNOWN. No bond yield value was invented."
        )
    if not os.path.exists(erp_json):
        warnings.append(
            f"{WARN_MISSING_ERP}: '{erp_json}' not found; ERP-dependent checks may "
            "be UNKNOWN. No ERP value was invented."
        )
    return warnings


def _count_unknown_checks(output: Dict[str, Any]) -> int:
    return sum(1 for c in output.get("checks", []) if c.get("result") == "UNKNOWN")


def run_real_dashboard_bootstrap(
    *,
    tickers: Optional[str | List[str]] = None,
    watchlist_path: Optional[str] = None,
    market: str = "US",
    valuation_date: str = "auto",
    db_path: str = DEFAULT_DB,
    refresh: bool = False,
    persist: bool = True,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    continue_on_error: bool = True,
    min_success_count: int = 1,
    assumptions_path: str = DEFAULT_ASSUMPTIONS,
    schema_path: str = DEFAULT_SCHEMA,
    bond_csv: str = DEFAULT_BOND_CURATED,
    erp_json: str = DEFAULT_ERP_CURATED,
    sec_dir: Optional[str] = None,
) -> Dict[str, Any]:
    from sws_engine.orchestration.company_run import run_company_analysis

    requested = _resolve_tickers(tickers, watchlist_path)
    os.makedirs(output_dir, exist_ok=True)

    vdate = None if (valuation_date or "auto") == "auto" else valuation_date
    global_warnings = _curated_source_warnings(bond_csv, erp_json)
    # P1.2-cal (B1): the curated rates were previously used only for warnings
    # and never reached the live payload, leaving risk_free_rate_10y_5y_avg a
    # critical_missing_input even with a valid --bond-csv. Build mapper-format
    # override specs once per run and inject them into every payload with
    # honest curated_rates/assumption/E2 lineage.
    from sws_engine.rates.injection import build_curated_rates_overrides
    from datetime import date as _date
    rates_injection = build_curated_rates_overrides(
        bond_csv, erp_json, country=market or "US",
        valuation_date=vdate or _date.today().isoformat())
    rates_overrides = rates_injection["overrides"]
    global_warnings.extend(rates_injection["warnings"])

    provider = None
    provider_error: Optional[str] = None
    try:
        provider = _provider(refresh=refresh)
    except Exception as exc:  # dependency missing etc. -> everything fails cleanly
        provider_error = f"{exc.__class__.__name__}: {exc}"

    results: List[Dict[str, Any]] = []
    persisted_count = 0
    warnings_count = len(global_warnings)
    unknown_total = 0
    profile_counts: Dict[str, int] = {}

    db = None
    if persist:
        from sws_engine.api.db_adapter import ApiDbAdapter
        db = ApiDbAdapter(db_path, assumptions_path)

    try:
        for ticker in requested:
            item: Dict[str, Any] = {"ticker": ticker, "status": "FAIL", "run_id": None,
                                    "error": None, "warnings_count": 0,
                                    "unknown_checks_count": None, "provider_profile": None}
            try:
                if provider is None:
                    raise RuntimeError(provider_error or "live provider unavailable")
                payload = provider.build_payload(
                    ticker, valuation_date=vdate, market=market, industry=None,
                    overrides=rates_overrides or None)
                if sec_dir:
                    # P1.3b (B4/B8): merge SEC official-filing values with
                    # documented sec_precedence; conflicts stay visible in
                    # payload.source_conflicts, provider_profile unchanged.
                    from sws_engine.sec.payload_merge import merge_sec_updates_from_dir
                    sec_report = merge_sec_updates_from_dir(payload, sec_dir)
                    item["sec_enrichment"] = {
                        "reason_code": sec_report["reason_code"],
                        "applied_fields_count": len(sec_report["applied_fields"]),
                        "conflicts_count": len(sec_report["conflicts"]),
                    }
                output = run_company_analysis(payload, assumptions_path, schema_path)

                # persist artifacts to disk (audit trail)
                p_path = os.path.join(output_dir, f"{ticker}_payload.json")
                o_path = os.path.join(output_dir, f"{ticker}_output.json")
                with open(p_path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2)
                with open(o_path, "w", encoding="utf-8") as fh:
                    json.dump(output, fh, indent=2)
                try:
                    from sws_engine.reporting.report import company_report_md
                    with open(os.path.join(output_dir, f"{ticker}_report.md"), "w", encoding="utf-8") as fh:
                        fh.write(company_report_md(output))
                except Exception:
                    pass  # report rendering is best-effort; output JSON is authoritative

                if db is not None:
                    item["run_id"] = db.save_company_output(output, payload)
                    persisted_count += 1

                item["status"] = "PASS"
                item["provider_profile"] = output.get("provider_profile")
                item["warnings_count"] = len(output.get("warnings", []) or [])
                item["unknown_checks_count"] = _count_unknown_checks(output)
                warnings_count += item["warnings_count"]
                unknown_total += item["unknown_checks_count"]
                prof = item["provider_profile"] or "unknown"
                profile_counts[prof] = profile_counts.get(prof, 0) + 1
            except Exception as exc:
                item["error"] = f"{exc.__class__.__name__}: {exc}"
                if not continue_on_error:
                    results.append(item)
                    break
            results.append(item)
    finally:
        if db is not None:
            db.close()

    succeeded = [r["ticker"] for r in results if r["status"] == "PASS"]
    failed = [{"ticker": r["ticker"], "error": r["error"]}
              for r in results if r["status"] != "PASS"]
    status = "PASS_WITH_LIMITATIONS" if len(succeeded) >= max(min_success_count, 0) else "FAIL"

    next_commands = {
        "api": "PYTHONPATH=src uvicorn sws_engine.api.app:app --host 127.0.0.1 --port 8000",
        "dashboard": "DASHBOARD_API_URL=http://127.0.0.1:8000 streamlit run dashboard/app.py",
    }
    summary = {
        "generated_at": _utc_now(),
        "status": status,
        "market": market,
        "valuation_date": valuation_date,
        "tickers_requested": requested,
        "tickers_succeeded": succeeded,
        "tickers_failed": failed,
        "persisted_count": persisted_count,
        "warnings_count": warnings_count,
        "unknown_checks_count": unknown_total,
        "provider_profile_counts": profile_counts,
        "global_warnings": global_warnings,
        "db_path": db_path,
        "output_dir": output_dir,
        "next_commands": next_commands,
        "notes": [
            "Missing analytical inputs remain missing (UNKNOWN policy preserved).",
            "Missing curated rates/ERP do not stop the bootstrap.",
            "production-readiness status is NOT changed by this command.",
        ],
        "results": results,
    }

    summary_path = os.path.join(output_dir, "bootstrap_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    report_path = os.path.join(output_dir, "bootstrap_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(_render_report_md(summary))
    summary["summary_path"] = summary_path
    summary["report_path"] = report_path
    return summary


def _render_report_md(summary: Dict[str, Any]) -> str:
    lines = [
        "# Real Dashboard Bootstrap Report",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Status: **{summary['status']}**",
        f"- Market: {summary['market']}",
        f"- Valuation date: {summary['valuation_date']}",
        f"- DB path: `{summary['db_path']}`",
        f"- Persisted runs: {summary['persisted_count']}",
        f"- Total warnings: {summary['warnings_count']}",
        f"- Total UNKNOWN checks: {summary['unknown_checks_count']}",
        f"- Provider profile counts: `{json.dumps(summary['provider_profile_counts'])}`",
        "",
        "## Global source warnings",
        "",
    ]
    if summary["global_warnings"]:
        lines += [f"- {w}" for w in summary["global_warnings"]]
    else:
        lines.append("- none")
    lines += ["", "## Per-ticker results", "",
              "| Ticker | Status | Run ID | Warnings | UNKNOWN checks | Provider profile | Error |",
              "|---|---|---|---:|---:|---|---|"]
    for r in summary["results"]:
        lines.append(
            f"| {r['ticker']} | {r['status']} | {r['run_id'] or '-'} | "
            f"{r['warnings_count']} | {r['unknown_checks_count'] if r['unknown_checks_count'] is not None else '-'} | "
            f"{r['provider_profile'] or '-'} | {r['error'] or '-'} |")
    lines += [
        "",
        "## Next commands",
        "",
        "```bash",
        summary["next_commands"]["api"],
        summary["next_commands"]["dashboard"],
        "```",
        "",
        "## Notes",
        "",
    ]
    lines += [f"- {n}" for n in summary["notes"]]
    lines += ["", "---", "", FOOTER, ""]
    return "\n".join(lines)


def today_iso() -> str:
    return date.today().isoformat()
