"""Phase 4 tests: store round-trip, batch with error isolation, and the
acceptance criterion - two runs on different dates queryable as history."""
import json
import os

import sws_engine
from sws_engine.db.store import Store, assumptions_hash
from sws_engine.orchestration.batch import run_batch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = lambda *p: os.path.join(ROOT, *p)


def _batch(db, date, overrides=None):
    return run_batch(
        watchlist_path=D("data", "watchlists", "watchlist_synthetic.csv"),
        valuation_date=date, db_path=db,
        universe_csv=D("data", "universe", "universe_US-SYN.csv"),
        market="US-SYN",
        assumptions_path=D("config", "assumptions.yaml"),
        schema_path=D("schemas", "output_schema.json"),
        bond_csv=D("data", "rates", "bond_yields_10y.csv"),
        erp_json=D("data", "rates", "erp.json"),
        savings_rate=0.02, cpi=0.028, workers=2,
        payload_overrides_by_ticker=overrides)


def test_batch_error_isolation_and_report(tmp_path):
    db = str(tmp_path / "sws.db")
    report = _batch(db, "2026-07-06")
    # GHOST snapshot doesn't exist -> SKIPPED; the others must still PASS
    assert {r["ticker"] for r in report["PASS"]} == {"SYN-ACME", "SYN-BURN"}
    assert {r["ticker"] for r in report["SKIPPED"]} == {"SYN-GHOST"}
    assert report["FAIL"] == []
    st = Store(db)
    # output JSON is the source of truth and round-trips completely
    out = st.latest_output("SYN-ACME")
    assert len([c for c in out["checks"] if c["axis"] != "management"]) == 30
    assert out["valuation_variant"] == "base"
    # extracted columns match the JSON (index-only rule)
    row = st.conn.execute(
        "SELECT score_health, coverage_health, fair_value FROM outputs "
        "WHERE ticker='SYN-ACME'").fetchone()
    assert row["score_health"] == out["scores"]["health"]["score_raw"]
    assert abs(row["fair_value"] - out["fair_value"]) < 1e-9
    # checks are filterable for the screener
    unknowns = st.checks_query(ticker="SYN-BURN", result="UNKNOWN")
    assert len(unknowns) > 0
    # provenance: run carries assumptions hash + engine version
    run = st.conn.execute("SELECT * FROM runs WHERE ticker='SYN-ACME'").fetchone()
    assert run["assumptions_hash"] == assumptions_hash(D("config", "assumptions.yaml"))
    assert run["engine_version"] == sws_engine.__version__
    # averages snapshot persisted
    av = st.conn.execute("SELECT * FROM averages_snapshots").fetchone()
    assert av["market"] == "US-SYN" and av["as_of"] == "2026-07-06"
    st.close()


def test_acceptance_two_dates_history_one_select(tmp_path):
    """Acceptance Phase 4: runs on two different dates for the same ticker,
    'how did the Health score evolve' answered by one SELECT."""
    db = str(tmp_path / "sws.db")
    _batch(db, "2026-07-05")
    # day 2: leverage deteriorates -> Health score must drop
    _batch(db, "2026-07-06", overrides={
        "SYN-ACME": {"total_debt": 3.6e9, "debt_current": 3.6e9,
                     "operating_cash_flow": 500e6}})
    st = Store(db)
    hist = st.score_history("SYN-ACME", "health", since_date="2026-06-08")
    st.close()
    assert [h["valuation_date"] for h in hist] == ["2026-07-05", "2026-07-06"]
    assert hist[1]["score_raw"] < hist[0]["score_raw"]
    # coverage always returned next to the score (runbook rule)
    assert all("coverage_pct" in h for h in hist)


def test_screener_filters_score_and_coverage(tmp_path):
    db = str(tmp_path / "sws.db")
    _batch(db, "2026-07-06")
    st = Store(db)
    rows = st.screener(axis="health", min_score=4, min_coverage=0.8)
    tickers = [r["ticker"] for r in rows]
    assert "SYN-ACME" in tickers          # 5/6, coverage 1.0
    # BURN health: 4 known of 6 -> coverage 0.83 but score 4 -> included;
    # tighten coverage to prove the filter bites
    strict = st.screener(axis="value", min_score=1, min_coverage=0.9)
    assert all(r["coverage_pct"] >= 0.9 for r in strict)
    st.close()


def test_portfolio_persistence_roundtrip(tmp_path):
    from sws_engine.portfolio.portfolio_run import run_portfolio_analysis
    db = str(tmp_path / "sws.db")
    st = Store(db)
    st.init_schema()
    definition = json.load(open(D("tests", "fixtures", "demo_portfolio.json")))
    pid = st.save_portfolio("demo", definition)
    out = run_portfolio_analysis(definition, {})
    rid = st.save_portfolio_run(pid, out)
    row = st.conn.execute(
        "SELECT * FROM portfolio_runs WHERE run_id=?", (rid,)).fetchone()
    saved = json.loads(row["output_json"])
    assert abs(saved["returns_per_position"]["AMZN"]["total_return"]
               - 1.0015) < 0.001
    st.close()
