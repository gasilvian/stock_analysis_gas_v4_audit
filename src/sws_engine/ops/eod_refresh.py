"""EOD refresh orchestration (Plan E).

This runner is intentionally provider-aware and degradation-safe. It can run
in synthetic/recorded mode or live yfinance mode; failures are isolated per
ticker and logged. It is not a daemon and does not require network unless the
caller chooses --provider yfinance-live.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sws_engine.orchestration.batch import run_batch
from sws_engine.rates.sources import rates_source_report


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir(path: str | os.PathLike) -> None:
    os.makedirs(path, exist_ok=True)


def load_watchlist(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def refresh_recorded_snapshots_from_yfinance(watchlist: list[dict], out_dir: str, refresh: bool = False) -> dict:
    """Record live yfinance snapshots for a watchlist.

    If yfinance is not installed or a ticker fails, the report records FAIL but
    does not stop the refresh. Normal CI should not call this function.
    """
    _ensure_dir(out_dir)
    report = {"PASS": [], "FAIL": [], "SKIPPED": []}
    try:
        from sws_engine.providers.yfinance_live import YFinanceLiveProvider
        from sws_engine.data.recorded_fixtures import save_recorded_snapshot
    except Exception as exc:  # dependency isolation
        for row in watchlist:
            report["FAIL"].append({"ticker": row.get("ticker"), "error": f"live provider unavailable: {exc}"})
        return report
    provider = YFinanceLiveProvider(refresh=refresh)
    for row in watchlist:
        ticker = row.get("ticker")
        if not ticker:
            report["SKIPPED"].append({"ticker": None, "error": "missing ticker"})
            continue
        try:
            snap = provider.fetch_raw_snapshot(ticker)
            path = os.path.join(out_dir, f"{ticker}_snapshot.json")
            save_recorded_snapshot(ticker, snap, path)
            report["PASS"].append({"ticker": ticker, "snapshot_path": path})
        except Exception as exc:
            report["FAIL"].append({"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"})
    return report


def run_eod_refresh(*, valuation_date: str, watchlist_path: str, db_path: str,
                    universe_csv: str, market: str, assumptions_path: str,
                    schema_path: str, bond_csv: str, erp_json: str, fx_csv: str,
                    logs_dir: str = "logs", workers: int = 2,
                    provider_mode: str = "recorded", refresh_live: bool = False,
                    recorded_out_dir: str = "data/recorded_yfinance") -> dict:
    """Run a daily refresh and write an operational JSON log.

    provider_mode:
      - recorded: use watchlist snapshot_path entries as-is through batch;
      - yfinance-live: first record fresh snapshots, then caller can use the
        generated report to build a live watchlist in a later operational step.
    """
    _ensure_dir(logs_dir)
    status = {
        "started_at": _now(),
        "valuation_date": valuation_date,
        "provider_mode": provider_mode,
        "watchlist_path": watchlist_path,
        "rates_sources": rates_source_report(bond_csv=bond_csv, erp_json=erp_json, fx_csv=fx_csv),
        "snapshot_refresh": None,
        "batch_report": None,
        "alerts": [],
    }
    if provider_mode == "yfinance-live":
        status["snapshot_refresh"] = refresh_recorded_snapshots_from_yfinance(load_watchlist(watchlist_path), recorded_out_dir, refresh=refresh_live)
        fail_count = len(status["snapshot_refresh"].get("FAIL", []))
        total = sum(len(status["snapshot_refresh"].get(k, [])) for k in ("PASS", "FAIL", "SKIPPED")) or 1
        if fail_count / total > 0.2:
            status["alerts"].append(f"ALERT: live snapshot failures exceed 20% ({fail_count}/{total})")
    # The existing batch path stays deterministic and recorded/snapshot based.
    status["batch_report"] = run_batch(
        watchlist_path=watchlist_path, valuation_date=valuation_date, db_path=db_path,
        universe_csv=universe_csv, market=market, assumptions_path=assumptions_path,
        schema_path=schema_path, bond_csv=bond_csv, erp_json=erp_json, workers=workers)
    fail_count = len(status["batch_report"].get("FAIL", []))
    total = sum(len(status["batch_report"].get(k, [])) for k in ("PASS", "FAIL", "SKIPPED")) or 1
    if fail_count / total > 0.2:
        status["alerts"].append(f"ALERT: batch failures exceed 20% ({fail_count}/{total})")
    status["finished_at"] = _now()
    log_path = Path(logs_dir) / f"eod_refresh_{valuation_date}.json"
    with log_path.open("w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=2)
    status["log_path"] = str(log_path)
    return status
