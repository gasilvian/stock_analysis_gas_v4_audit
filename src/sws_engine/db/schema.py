"""DB schema v1 (Phase 4.1). Portable SQL subset: TEXT/REAL/INTEGER,
application-generated ids, no engine-specific features, so the same DDL
runs on SQLite now and Postgres later (swap driver + paramstyle in Store).

Rule: the output JSON is the source of truth; extracted columns exist only
as query indexes and are never edited independently."""

DDL = [
    """CREATE TABLE IF NOT EXISTS instruments (
        ticker TEXT PRIMARY KEY,
        exchange TEXT,
        company_type TEXT,
        currency TEXT,
        industry TEXT,
        market TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS input_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        provider_profile TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        valuation_date TEXT NOT NULL,
        snapshot_id TEXT,
        assumptions_hash TEXT NOT NULL,
        engine_version TEXT NOT NULL,
        status TEXT NOT NULL,           -- PASS | FAIL | SKIPPED
        error TEXT,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS outputs (
        run_id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        valuation_date TEXT NOT NULL,
        output_json TEXT NOT NULL,      -- schema-validated, source of truth
        fair_value REAL, price REAL, discount_pct REAL,
        valuation_model TEXT, valuation_variant TEXT,
        score_value INTEGER, score_future INTEGER, score_past INTEGER,
        score_health INTEGER, score_dividend INTEGER,
        coverage_value REAL, coverage_future REAL, coverage_past REAL,
        coverage_health REAL, coverage_dividend REAL
    )""",
    """CREATE TABLE IF NOT EXISTS checks (
        run_id TEXT NOT NULL,
        ticker TEXT NOT NULL,
        valuation_date TEXT NOT NULL,
        axis TEXT NOT NULL,
        check_id TEXT NOT NULL,
        name TEXT NOT NULL,
        result TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        source_quality TEXT NOT NULL,
        PRIMARY KEY (run_id, axis, check_id)
    )""",
    """CREATE TABLE IF NOT EXISTS averages_snapshots (
        market TEXT NOT NULL,
        as_of TEXT NOT NULL,
        snapshot_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (market, as_of)
    )""",
    """CREATE TABLE IF NOT EXISTS portfolios (
        portfolio_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        definition_json TEXT NOT NULL,  -- positions + transactions
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS portfolio_runs (
        run_id TEXT PRIMARY KEY,
        portfolio_id TEXT NOT NULL,
        valuation_date TEXT NOT NULL,
        output_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_outputs_ticker_date ON outputs (ticker, valuation_date)",
    "CREATE INDEX IF NOT EXISTS idx_checks_filter ON checks (axis, result, reason_code)",
    "CREATE INDEX IF NOT EXISTS idx_runs_ticker_date ON runs (ticker, valuation_date)",
]
