from pathlib import Path

from sws_engine.rates.curated import (
    build_curated_bond_csv_from_export,
    validate_bond_curated_csv,
    validate_erp_curated_json,
)


def test_refresh_rates_from_fred_export_writes_curated_csv(tmp_path):
    out = tmp_path / "bond_yields_10y_curated.csv"
    rep = build_curated_bond_csv_from_export(
        input_csv="tests/fixtures/rates/fred_DGS10.csv",
        output_csv=out,
        country="US",
        currency="USD",
        series_id="DGS10",
        review_status="operator_review_required",
    )
    assert rep["status"] == "PASS_WITH_LIMITATIONS"
    assert rep["observations_written"] == 3
    text = out.read_text(encoding="utf-8")
    assert "0.04150000" in text
    assert "operator_review_required" in text
    val = validate_bond_curated_csv(out)
    assert val["status"] == "PASS"


def test_validate_bond_curated_require_reviewed_flags_draft(tmp_path):
    out = tmp_path / "bond.csv"
    build_curated_bond_csv_from_export(
        input_csv="tests/fixtures/rates/fred_DGS10.csv",
        output_csv=out,
        review_status="operator_review_required",
    )
    val = validate_bond_curated_csv(out, require_reviewed=True)
    assert val["status"] == "NOT_READY"
    assert any(m["code"] == "BOND_CSV_REVIEW_REQUIRED" for m in val["messages"])


def test_validate_erp_curated_review_lifecycle():
    ok = validate_erp_curated_json("tests/fixtures/rates/erp_curated_reviewed.json", require_reviewed=True)
    assert ok["status"] == "PASS"
    assert ok["lineage"]["source_quality"] == "assumption"
    draft = validate_erp_curated_json("tests/fixtures/rates/erp_curated_draft.json", require_reviewed=True)
    assert draft["status"] == "NOT_READY"
    assert any(m["code"] == "ERP_REVIEW_REQUIRED" for m in draft["messages"])
