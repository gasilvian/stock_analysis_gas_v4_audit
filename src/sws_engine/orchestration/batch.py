"""Batch runner (Phase 4.2): builds payloads from recorded snapshots,
runs the engine per ticker, persists everything to the Store.

- Watchlist CSV: ticker,snapshot_path,industry,country,market
- Error isolation: one failed ticker never stops the batch; every ticker
  ends as PASS / FAIL (run error persisted) / SKIPPED (snapshot missing).
- Bounded concurrency (small thread pool - future live providers have
  rate limits; SQLite writes are serialized through a lock)."""
import csv
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import sws_engine
from sws_engine.averages.builder import build_averages, load_universe
from sws_engine.db.store import Store, assumptions_hash
from sws_engine.orchestration.company_run import run_company_analysis
from sws_engine.orchestration.payload_builder import build_company_payload

DEFAULT_WORKERS = 2


def load_watchlist(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _process_ticker(entry, *, valuation_date, averages, assumptions_path,
                    schema_path, bond_csv, erp_json, store, lock, ahash,
                    overrides=None):
    ticker = entry["ticker"]
    snap_path = entry["snapshot_path"]
    if not os.path.exists(snap_path):
        with lock:
            store.create_run(ticker=ticker, valuation_date=valuation_date,
                             snapshot_id=None, assumptions_hash=ahash,
                             engine_version=sws_engine.__version__,
                             status="SKIPPED",
                             error=f"snapshot not found: {snap_path}")
        return ticker, "SKIPPED", None
    try:
        payload, _pr = build_company_payload(
            snapshot_path=snap_path, averages_snapshot=averages,
            industry=entry["industry"], country=entry["country"],
            valuation_date=valuation_date, bond_csv=bond_csv,
            erp_json=erp_json, overrides=overrides)
        output = run_company_analysis(payload, assumptions_path, schema_path)
        with lock:
            store.upsert_instrument(
                ticker=ticker, exchange=payload.get("exchange"),
                company_type=payload.get("company_type"),
                currency=payload.get("currency"),
                industry=entry["industry"], market=entry.get("market"))
            sid = store.save_input_snapshot(ticker, payload)
            rid = store.create_run(
                ticker=ticker, valuation_date=valuation_date,
                snapshot_id=sid, assumptions_hash=ahash,
                engine_version=sws_engine.__version__, status="PASS")
            store.save_output(rid, output)
        return ticker, "PASS", None
    except Exception as exc:  # error isolation: record and continue
        with lock:
            store.create_run(ticker=ticker, valuation_date=valuation_date,
                             snapshot_id=None, assumptions_hash=ahash,
                             engine_version=sws_engine.__version__,
                             status="FAIL", error=f"{type(exc).__name__}: {exc}")
        return ticker, "FAIL", str(exc)


def run_batch(*, watchlist_path, valuation_date, db_path, universe_csv,
              market, assumptions_path, schema_path,
              bond_csv="data/rates/bond_yields_10y.csv",
              erp_json="data/rates/erp.json",
              savings_rate=None, cpi=None, workers=DEFAULT_WORKERS,
              payload_overrides_by_ticker=None) -> dict:
    """Runs the full daily sequence from runbook.md section 2:
    averages -> per-ticker payload -> engine -> persist. Returns the batch
    report {PASS: [...], FAIL: [...], SKIPPED: [...]}."""
    store = Store(db_path)
    store.init_schema()
    lock = threading.Lock()
    ahash = assumptions_hash(assumptions_path)

    averages = build_averages(load_universe(universe_csv),
                              as_of=valuation_date,
                              savings_rate=savings_rate, cpi=cpi)
    store.save_averages_snapshot(market, averages)

    entries = load_watchlist(watchlist_path)
    overrides = payload_overrides_by_ticker or {}
    results = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = []
        for e in entries:
            def task(entry=e):
                r = _process_ticker(
                    entry, valuation_date=valuation_date, averages=averages,
                    assumptions_path=assumptions_path, schema_path=schema_path,
                    bond_csv=bond_csv, erp_json=erp_json, store=store,
                    lock=lock, ahash=ahash,
                    overrides=overrides.get(entry["ticker"]))
                return r
            futures.append(pool.submit(task))
        for f in as_completed(futures):
            results.append(f.result())

    report = store.batch_report(valuation_date)
    store.close()
    return report
