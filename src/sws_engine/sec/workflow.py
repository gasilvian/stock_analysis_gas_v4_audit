"""Operational workflow for `refresh-sec-financials` CLI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sws_engine.sec.cik_resolver import resolve_cik
from sws_engine.sec.companyfacts_adapter import get_companyfacts
from sws_engine.sec.mapping_report import mapping_report_md
from sws_engine.sec.statement_snapshot import build_statement_snapshot


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def refresh_sec_financials(
    *,
    tickers: str,
    output_dir: str | Path,
    cik_map: str | Path,
    companyfacts_dir: str | Path | None = None,
    valuation_date: str | None = None,
    live: bool = False,
    refresh: bool = False,
    continue_on_error: bool = True,
    user_agent: str | None = None,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    raw_dir = out_dir / "raw" / "companyfacts"
    normalized_dir = out_dir / "normalized"
    reports_dir = out_dir / "mapping_reports"
    succeeded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for ticker in [t.strip().upper() for t in tickers.split(",") if t.strip()]:
        try:
            record = resolve_cik(ticker, cik_map)
            if not record:
                skipped.append({"ticker": ticker, "reason_code": "CIK_NOT_FOUND"})
                if not continue_on_error:
                    break
                continue
            kwargs: dict[str, Any] = {}
            if user_agent:
                kwargs["user_agent"] = user_agent
            facts, source_path = get_companyfacts(
                record.cik10,
                cache_dir=raw_dir,
                fixture_dir=companyfacts_dir,
                live=live,
                refresh=refresh,
                **kwargs,
            )
            # Ensure raw is also copied into output for reproducibility.
            _write_json(raw_dir / f"CIK{record.cik10}.json", facts)
            snapshot = build_statement_snapshot(
                facts,
                cik_record=record,
                source_path=str(raw_dir / f"CIK{record.cik10}.json"),
                valuation_date=valuation_date,
            )
            json_path = normalized_dir / f"{ticker}_sec_statement_snapshot.json"
            payload_path = normalized_dir / f"{ticker}_sec_payload_updates.json"
            report_json_path = reports_dir / f"{ticker}_sec_mapping_report.json"
            report_md_path = reports_dir / f"{ticker}_sec_mapping_report.md"
            _write_json(json_path, snapshot)
            _write_json(payload_path, snapshot.get("payload_updates") or {})
            _write_json(report_json_path, snapshot.get("mapping_report") or {})
            _write_text(report_md_path, mapping_report_md(snapshot))
            succeeded.append({
                "ticker": ticker,
                "cik": record.cik10,
                "status": snapshot.get("status"),
                "snapshot_path": str(json_path),
                "payload_updates_path": str(payload_path),
                "mapping_report_path": str(report_json_path),
                "mapping_report_md_path": str(report_md_path),
                "mapped_fields_count": len((snapshot.get("mapping_report") or {}).get("mapped_fields") or []),
                "unmapped_fields_count": len((snapshot.get("mapping_report") or {}).get("unmapped_fields") or []),
            })
        except Exception as exc:  # noqa: BLE001 - operational batch must isolate ticker failures
            failed.append({"ticker": ticker, "error": f"{exc.__class__.__name__}: {exc}"})
            if not continue_on_error:
                break
    status = "PASS_WITH_LIMITATIONS" if succeeded and not failed else "PARTIAL" if succeeded else "FAIL"
    report = {
        "status": status,
        "scope": "v4.0-p0.3-sec-first-financial-statements-foundation",
        "output_dir": str(out_dir),
        "tickers_succeeded": succeeded,
        "tickers_failed": failed,
        "tickers_skipped": skipped,
        "live_mode": bool(live),
        "refresh": bool(refresh),
        "unknown_policy": "Missing CIKs or XBRL tags are reported as skipped/UNKNOWN; no values are fabricated.",
    }
    _write_json(out_dir / "sec_refresh_report.json", report)
    return report
