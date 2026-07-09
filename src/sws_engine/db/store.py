"""Store (Phase 4.1): SQLite now, Postgres-compatible by swapping the
connection factory and paramstyle. All writes are idempotent per
(run/snapshot id); the output JSON is authoritative."""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from sws_engine.db.schema import DDL

AXES = ("value", "future", "past", "health", "dividend")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(obj) -> str:
    if isinstance(obj, (dict, list)):
        obj = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(str(obj).encode("utf-8")).hexdigest()


def assumptions_hash(assumptions_path: str) -> str:
    with open(assumptions_path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class Store:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # check_same_thread=False is safe here: the batch runner serializes
        # all writes through a single lock (see orchestration/batch.py)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self):
        cur = self.conn.cursor()
        for stmt in DDL:
            cur.execute(stmt)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # -- writes ------------------------------------------------------------
    def upsert_instrument(self, *, ticker, exchange=None, company_type=None,
                          currency=None, industry=None, market=None):
        self.conn.execute(
            """INSERT INTO instruments (ticker, exchange, company_type,
               currency, industry, market) VALUES (?,?,?,?,?,?)
               ON CONFLICT(ticker) DO UPDATE SET
               exchange=excluded.exchange, company_type=excluded.company_type,
               currency=excluded.currency, industry=excluded.industry,
               market=excluded.market""",
            (ticker, exchange, company_type, currency, industry, market))
        self.conn.commit()

    def save_input_snapshot(self, ticker: str, payload: dict) -> str:
        sid = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO input_snapshots (snapshot_id, ticker,
               provider_profile, payload_json, payload_hash, created_at)
               VALUES (?,?,?,?,?,?)""",
            (sid, ticker, payload.get("provider_profile", ""),
             json.dumps(payload, sort_keys=True), sha256_of(payload), _now()))
        self.conn.commit()
        return sid

    def create_run(self, *, ticker, valuation_date, snapshot_id,
                   assumptions_hash, engine_version, status, error=None) -> str:
        rid = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO runs (run_id, ticker, valuation_date, snapshot_id,
               assumptions_hash, engine_version, status, error, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (rid, ticker, valuation_date, snapshot_id, assumptions_hash,
             engine_version, status, error, _now()))
        self.conn.commit()
        return rid

    def save_output(self, run_id: str, output: dict):
        s, c = {}, {}
        for a in AXES:
            s[a] = output["scores"][a]["score_raw"]
            c[a] = output["scores"][a]["coverage_pct"]
        self.conn.execute(
            """INSERT INTO outputs (run_id, ticker, valuation_date,
               output_json, fair_value, price, discount_pct, valuation_model,
               valuation_variant, score_value, score_future, score_past,
               score_health, score_dividend, coverage_value, coverage_future,
               coverage_past, coverage_health, coverage_dividend)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id, output["ticker"], output["valuation_date"],
             json.dumps(output, sort_keys=True), output.get("fair_value"),
             output.get("price"), output.get("discount_pct"),
             output.get("valuation_model"), output.get("valuation_variant"),
             s["value"], s["future"], s["past"], s["health"], s["dividend"],
             c["value"], c["future"], c["past"], c["health"], c["dividend"]))
        rows = [(run_id, output["ticker"], output["valuation_date"],
                 ch["axis"], str(ch["id"]), ch["name"], ch["result"],
                 ch["reason_code"], ch["source_quality"])
                for ch in output["checks"]]
        self.conn.executemany(
            """INSERT INTO checks (run_id, ticker, valuation_date, axis,
               check_id, name, result, reason_code, source_quality)
               VALUES (?,?,?,?,?,?,?,?,?)""", rows)
        self.conn.commit()

    def save_averages_snapshot(self, market: str, snapshot: dict):
        self.conn.execute(
            """INSERT INTO averages_snapshots (market, as_of, snapshot_json,
               created_at) VALUES (?,?,?,?)
               ON CONFLICT(market, as_of) DO UPDATE SET
               snapshot_json=excluded.snapshot_json,
               created_at=excluded.created_at""",
            (market, snapshot["meta"]["industry_averages_as_of"],
             json.dumps(snapshot, sort_keys=True), _now()))
        self.conn.commit()

    def save_portfolio(self, name: str, definition: dict) -> str:
        pid = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO portfolios (portfolio_id, name, definition_json,
               created_at) VALUES (?,?,?,?)""",
            (pid, name, json.dumps(definition, sort_keys=True), _now()))
        self.conn.commit()
        return pid

    def save_portfolio_run(self, portfolio_id: str, output: dict) -> str:
        rid = str(uuid.uuid4())
        self.conn.execute(
            """INSERT INTO portfolio_runs (run_id, portfolio_id,
               valuation_date, output_json, created_at) VALUES (?,?,?,?,?)""",
            (rid, portfolio_id, output["valuation_date"],
             json.dumps(output, sort_keys=True), _now()))
        self.conn.commit()
        return rid

    # -- queries -----------------------------------------------------------
    def latest_output(self, ticker: str) -> dict:
        row = self.conn.execute(
            """SELECT output_json FROM outputs WHERE ticker=?
               ORDER BY valuation_date DESC LIMIT 1""", (ticker,)).fetchone()
        return json.loads(row["output_json"]) if row else None

    def score_history(self, ticker: str, axis: str, since_date: str = None):
        """Answers 'how did the <axis> score evolve': one SELECT, score with
        its coverage (never score alone - runbook rule)."""
        if axis not in AXES:
            raise ValueError(f"axis must be one of {AXES}")
        q = (f"SELECT valuation_date, score_{axis} AS score_raw, "
             f"coverage_{axis} AS coverage_pct FROM outputs WHERE ticker=?")
        args = [ticker]
        if since_date:
            q += " AND valuation_date >= ?"
            args.append(since_date)
        q += " ORDER BY valuation_date ASC"
        return [dict(r) for r in self.conn.execute(q, args).fetchall()]

    def screener(self, *, axis: str, min_score: int = 0,
                 min_coverage: float = 0.66, valuation_date: str = None):
        """Latest run per ticker filtered by score AND coverage (coverage
        filter is mandatory by design - no score comparison without it)."""
        if axis not in AXES:
            raise ValueError(f"axis must be one of {AXES}")
        q = (f"""SELECT o.ticker, o.valuation_date, o.score_{axis} AS score_raw,
                 o.coverage_{axis} AS coverage_pct, o.fair_value, o.price,
                 o.discount_pct
                 FROM outputs o
                 JOIN (SELECT ticker, MAX(valuation_date) AS md FROM outputs
                       {"WHERE valuation_date=?" if valuation_date else ""}
                       GROUP BY ticker) last
                 ON o.ticker=last.ticker AND o.valuation_date=last.md
                 WHERE o.score_{axis} >= ? AND o.coverage_{axis} >= ?
                 ORDER BY o.score_{axis} DESC, o.coverage_{axis} DESC""")
        args = ([valuation_date] if valuation_date else []) + \
            [min_score, min_coverage]
        return [dict(r) for r in self.conn.execute(q, args).fetchall()]

    def checks_query(self, *, ticker=None, axis=None, result=None,
                     reason_code=None, valuation_date=None):
        q = "SELECT * FROM checks WHERE 1=1"
        args = []
        for col, val in (("ticker", ticker), ("axis", axis),
                         ("result", result), ("reason_code", reason_code),
                         ("valuation_date", valuation_date)):
            if val is not None:
                q += f" AND {col}=?"
                args.append(val)
        return [dict(r) for r in self.conn.execute(q, args).fetchall()]

    def batch_report(self, valuation_date: str):
        rows = self.conn.execute(
            """SELECT ticker, status, error FROM runs WHERE valuation_date=?
               ORDER BY ticker""", (valuation_date,)).fetchall()
        rep = {"PASS": [], "FAIL": [], "SKIPPED": []}
        for r in rows:
            rep[r["status"]].append(
                {"ticker": r["ticker"], "error": r["error"]})
        return rep
