from sws_engine.rates.sources import rates_source_report


def test_rates_source_report_classifies_existing_sources():
    rep = rates_source_report(
        bond_csv="data/rates/bond_yields_10y.csv",
        erp_json="data/rates/erp.json",
        fx_csv="data/fx/fx_eod.csv",
    )
    assert rep["bond_10y_5y_avg_source"]["exists"] is True
    assert rep["equity_risk_premium_source"]["exists"] is True
    assert rep["fx_eod_source"]["exists"] is True
    assert "note" in rep
