import json

from sws_engine.ops.eod_refresh import run_eod_refresh


def test_eod_refresh_recorded_writes_log(tmp_path):
    db = tmp_path / "sws.db"
    logs = tmp_path / "logs"
    rep = run_eod_refresh(
        valuation_date="2026-07-06",
        watchlist_path="data/watchlists/watchlist_synthetic.csv",
        db_path=str(db),
        universe_csv="data/universe/universe_US-SYN.csv",
        market="US-SYN",
        assumptions_path="config/assumptions.yaml",
        schema_path="schemas/output_schema.json",
        bond_csv="data/rates/bond_yields_10y.csv",
        erp_json="data/rates/erp.json",
        fx_csv="data/fx/fx_eod.csv",
        logs_dir=str(logs),
        workers=1,
    )
    assert rep["batch_report"]["PASS"]
    assert rep["log_path"]
    assert json.loads(open(rep["log_path"], encoding="utf-8").read())["valuation_date"] == "2026-07-06"
