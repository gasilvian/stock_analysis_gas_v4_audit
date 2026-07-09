"""Operational query endpoints for the real-data dashboard bootstrap.

Read-only endpoints over the existing SQLite store. They add no new model
semantics: the output JSON stays the source of truth and no score is exposed
without its coverage.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from sws_engine.api.db_adapter import AXES, ApiDbAdapter
from sws_engine.api.deps import get_db_adapter
from sws_engine.api.security import require_api_key

router = APIRouter(tags=["meta"], dependencies=[Depends(require_api_key)])


@router.get("/meta/runtime-summary")
def runtime_summary(db: ApiDbAdapter = Depends(get_db_adapter)) -> Dict[str, Any]:
    conn = db.store.conn
    runs_count = conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
    latest = conn.execute("SELECT MAX(created_at) AS m FROM runs").fetchone()["m"]
    tickers = [r["ticker"] for r in conn.execute(
        "SELECT DISTINCT ticker FROM outputs ORDER BY ticker").fetchall()]
    return {
        "db_path": db.db_path,
        "company_runs_count": runs_count,
        "latest_run_at": latest,
        "tickers_available": tickers,
        "production_readiness_hint": (
            "Run CLI production-readiness for authoritative status"
        ),
    }


@router.get("/companies")
def list_companies(db: ApiDbAdapter = Depends(get_db_adapter)) -> Dict[str, List[Dict[str, Any]]]:
    conn = db.store.conn
    rows = conn.execute(
        """SELECT o.ticker, o.valuation_date, o.output_json,
                  o.coverage_value, o.coverage_future, o.coverage_past,
                  o.coverage_health, o.coverage_dividend
           FROM outputs o
           JOIN (SELECT ticker, MAX(valuation_date) AS md FROM outputs
                 GROUP BY ticker) last
           ON o.ticker = last.ticker AND o.valuation_date = last.md
           ORDER BY o.ticker""").fetchall()
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if row["ticker"] in seen:
            continue
        seen.add(row["ticker"])
        parsed = json.loads(row["output_json"])
        out.append({
            "ticker": row["ticker"],
            "latest_valuation_date": row["valuation_date"],
            "provider_profile": parsed.get("provider_profile"),
            "coverage_summary": {ax: row[f"coverage_{ax}"] for ax in AXES},
            "unknown_checks_count": sum(
                1 for c in parsed.get("checks", []) if c.get("result") == "UNKNOWN"),
            "warnings_count": len(parsed.get("warnings", []) or []),
        })
    return {"tickers": out}
