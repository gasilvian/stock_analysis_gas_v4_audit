"""Thin API adapter over the Phase 4 SQLite store.

The output JSON remains authoritative; extracted DB columns are used only for
query convenience. This module deliberately avoids changing Store semantics.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import sws_engine
from sws_engine.db.store import Store, assumptions_hash

AXES = ("value", "future", "past", "health", "dividend")


class ApiDbAdapter:
    def __init__(self, db_path: str, assumptions_path: str):
        self.db_path = db_path
        self.assumptions_path = assumptions_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.store = Store(db_path)
        self.store.init_schema()

    def close(self) -> None:
        self.store.close()

    def save_company_output(self, output: Dict[str, Any], input_payload: Optional[Dict[str, Any]] = None) -> str:
        payload = input_payload or output
        ticker = output["ticker"]
        self.store.upsert_instrument(
            ticker=ticker,
            exchange=output.get("exchange"),
            company_type=(input_payload or {}).get("company_type") if input_payload else None,
            currency=(input_payload or {}).get("currency") if input_payload else None,
            industry=(input_payload or {}).get("industry") if input_payload else None,
            market=(input_payload or {}).get("market") if input_payload else None,
        )
        snapshot_id = self.store.save_input_snapshot(ticker, payload)
        try:
            ahash = assumptions_hash(self.assumptions_path)
        except FileNotFoundError:
            ahash = "missing-assumptions-file"
        run_id = self.store.create_run(
            ticker=ticker,
            valuation_date=output["valuation_date"],
            snapshot_id=snapshot_id,
            assumptions_hash=ahash,
            engine_version=sws_engine.__version__,
            status="PASS",
        )
        self.store.save_output(run_id, output)
        return run_id

    def get_latest_company_with_run_id(self, ticker: str) -> Optional[Dict[str, Any]]:
        row = self.store.conn.execute(
            """SELECT o.run_id, o.output_json FROM outputs o
               WHERE o.ticker=? ORDER BY o.valuation_date DESC, o.rowid DESC LIMIT 1""",
            (ticker,),
        ).fetchone()
        if not row:
            return None
        return {"run_id": row["run_id"], "output": json.loads(row["output_json"])}

    def get_latest_company(self, ticker: str) -> Optional[Dict[str, Any]]:
        rec = self.get_latest_company_with_run_id(ticker)
        return rec["output"] if rec else None

    def _company_output_rows(self, ticker: str, from_date: str | None = None, to_date: str | None = None):
        q = "SELECT run_id, output_json FROM outputs WHERE ticker=?"
        args: list[Any] = [ticker]
        if from_date:
            q += " AND valuation_date >= ?"
            args.append(from_date)
        if to_date:
            q += " AND valuation_date <= ?"
            args.append(to_date)
        q += " ORDER BY valuation_date ASC, rowid ASC"
        return self.store.conn.execute(q, args).fetchall()

    def get_company_history(
        self,
        ticker: str,
        axis: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> List[Dict[str, Any]]:
        axes = [axis] if axis else list(AXES)
        rows = self._company_output_rows(ticker, from_date, to_date)
        points: list[dict[str, Any]] = []
        for row in rows:
            out = json.loads(row["output_json"])
            for ax in axes:
                if ax not in AXES:
                    raise ValueError(f"axis must be one of {AXES}")
                sc = out["scores"][ax]
                points.append({
                    "valuation_date": out["valuation_date"],
                    "score_raw": sc["score_raw"],
                    "known_checks_count": sc.get("known_checks_count"),
                    "unknown_checks_count": sc.get("unknown_checks_count"),
                    "coverage_pct": sc["coverage_pct"],
                    "provider_profile": out.get("provider_profile"),
                    "run_id": row["run_id"],
                    "axis": ax,
                })
        return points

    def get_company_checks(
        self,
        ticker: str,
        axis: str | None = None,
        result: str | None = None,
        reason_code: str | None = None,
        latest_only: bool = True,
    ) -> List[Dict[str, Any]]:
        if latest_only:
            rows = []
            rec = self.get_latest_company_with_run_id(ticker)
            if rec:
                rows.append({"run_id": rec["run_id"], "output": rec["output"]})
        else:
            rows = [
                {"run_id": r["run_id"], "output": json.loads(r["output_json"])}
                for r in self._company_output_rows(ticker)
            ]
        checks: list[dict[str, Any]] = []
        for row in rows:
            out = row["output"]
            for ch in out.get("checks", []):
                if axis and ch.get("axis") != axis:
                    continue
                if result and ch.get("result") != result:
                    continue
                if reason_code and ch.get("reason_code") != reason_code:
                    continue
                c = dict(ch)
                c["run_id"] = row["run_id"]
                c["valuation_date"] = out.get("valuation_date")
                checks.append(c)
        return checks

    def screener(
        self,
        axis: str | None = None,
        min_score: int | None = None,
        min_coverage: float | None = None,
        provider_profile: str | None = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        axes = [axis] if axis else list(AXES)
        if axis and axis not in AXES:
            raise ValueError(f"axis must be one of {AXES}")
        if min_score is None:
            min_score = 0
        if min_coverage is None:
            min_coverage = 0.66
        limit = max(1, min(int(limit), 500))
        rows = self.store.conn.execute(
            """SELECT o.run_id, o.output_json FROM outputs o
               JOIN (SELECT ticker, MAX(valuation_date) AS md FROM outputs GROUP BY ticker) last
               ON o.ticker=last.ticker AND o.valuation_date=last.md
               ORDER BY o.ticker ASC"""
        ).fetchall()
        result_rows: list[dict[str, Any]] = []
        for row in rows:
            out = json.loads(row["output_json"])
            if provider_profile and out.get("provider_profile") != provider_profile:
                continue
            selected_scores: dict[str, Any] = {}
            include = False
            for ax in axes:
                sc = out["scores"][ax]
                # Always couple score with coverage; never filter on score alone.
                if sc["score_raw"] >= min_score and sc["coverage_pct"] >= min_coverage:
                    include = True
                    selected_scores[ax] = {
                        "score_raw": sc["score_raw"],
                        "known_checks_count": sc.get("known_checks_count"),
                        "unknown_checks_count": sc.get("unknown_checks_count"),
                        "coverage_pct": sc["coverage_pct"],
                    }
                elif axis is None:
                    selected_scores[ax] = {
                        "score_raw": sc["score_raw"],
                        "known_checks_count": sc.get("known_checks_count"),
                        "unknown_checks_count": sc.get("unknown_checks_count"),
                        "coverage_pct": sc["coverage_pct"],
                    }
            if not include:
                continue
            result_rows.append({
                "ticker": out.get("ticker"),
                "exchange": out.get("exchange"),
                "valuation_date": out.get("valuation_date"),
                "provider_profile": out.get("provider_profile"),
                "fair_value": out.get("fair_value"),
                "price": out.get("price"),
                "discount_pct": out.get("discount_pct"),
                "scores": selected_scores,
                "warnings_count": len(out.get("warnings", [])),
                "run_id": row["run_id"],
            })
            if len(result_rows) >= limit:
                break
        return result_rows

    def save_portfolio_output(self, output: Dict[str, Any], input_payload: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        definition = input_payload or output
        portfolio_id = definition.get("portfolio_id") or definition.get("name")
        if portfolio_id:
            # Store keeps UUID primary keys; use a generated id but return it.
            pass
        name = definition.get("name") or definition.get("portfolio_id") or "api-portfolio"
        pid = self.store.save_portfolio(name, definition)
        run_id = self.store.save_portfolio_run(pid, output)
        return {"portfolio_id": pid, "run_id": run_id}

    def get_latest_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        row = self.store.conn.execute(
            """SELECT run_id, output_json FROM portfolio_runs WHERE portfolio_id=?
               ORDER BY valuation_date DESC, rowid DESC LIMIT 1""",
            (portfolio_id,),
        ).fetchone()
        if not row:
            return None
        return {"run_id": row["run_id"], "output": json.loads(row["output_json"])}

    def get_portfolio_history(self, portfolio_id: str) -> List[Dict[str, Any]]:
        rows = self.store.conn.execute(
            """SELECT run_id, valuation_date, output_json FROM portfolio_runs
               WHERE portfolio_id=? ORDER BY valuation_date ASC, rowid ASC""",
            (portfolio_id,),
        ).fetchall()
        points: list[dict[str, Any]] = []
        for row in rows:
            out = json.loads(row["output_json"])
            returns = out.get("returns_per_position") or {}
            total_return = None
            cagr = None
            for value in returns.values():
                if isinstance(value, dict):
                    total_return = value.get("total_return") if total_return is None else total_return
                    cagr = value.get("cagr") if cagr is None else cagr
            points.append({
                "run_id": row["run_id"],
                "valuation_date": row["valuation_date"],
                "portfolio_axis_scores": out.get("snowflake", {}).get("axis_scores") if out.get("snowflake") else None,
                "total_return": total_return,
                "cagr": cagr,
            })
        return points

    def get_averages_snapshot(self, market: str, date: str) -> Optional[Dict[str, Any]]:
        row = self.store.conn.execute(
            "SELECT snapshot_json FROM averages_snapshots WHERE market=? AND as_of=?",
            (market, date),
        ).fetchone()
        return json.loads(row["snapshot_json"]) if row else None

    def last_batch_run(self) -> Optional[str]:
        row = self.store.conn.execute(
            "SELECT created_at FROM runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return row["created_at"] if row else None
