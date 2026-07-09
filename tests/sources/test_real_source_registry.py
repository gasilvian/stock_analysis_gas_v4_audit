import csv
import json

from sws_engine.sources.real_sources import validate_source_registry, populate_real_sources


def test_source_registry_live_state_is_self_consistent_and_p11_sources_ready():
    """P1.1 update: this test previously pinned the live registry to
    NOT_READY, which was true while universe/bond/ERP were templates. Those
    sources are now genuinely populated and operator-approved (2026-07-09),
    so the pinned assertion became obsolete. The template-marker mechanism
    itself remains covered by the tmp_path tests below. Here we assert
    (a) self-consistency: status is NOT_READY iff blocking issues exist, and
    (b) the three historical blockers are ready and marker-free."""
    rep = validate_source_registry("config/source_registry.yaml", require_production=True).as_dict()
    if rep["blocking_issues"]:
        assert rep["status"] == "NOT_READY"
    else:
        assert rep["status"] == "PASS"
    by_id = {src["id"]: src for src in rep["sources"]}
    for sid in ("universe_us_curated", "bond_10y_5y_avg_curated", "erp_curated"):
        assert by_id[sid]["ready"] is True, sid
        assert by_id[sid]["looks_template_or_synthetic"] is False, sid


def test_populate_real_sources_handles_missing_live_dependency(monkeypatch, tmp_path):
    watchlist = tmp_path / "watchlist.csv"
    with watchlist.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["ticker", "industry", "market"])
        writer.writeheader()
        writer.writerow({"ticker": "AAPL", "industry": "Technology", "market": "US"})

    import builtins
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sws_engine.providers.yfinance_live":
            raise ImportError("simulated missing live provider")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rep = populate_real_sources(watchlist_path=str(watchlist), output_dir=str(tmp_path / "real"))
    assert rep["status"] == "FAIL"
    assert "Install live extra" in rep["hint"]


def test_real_source_registry_detects_template_markers_inside_target_files(tmp_path):
    target = tmp_path / "universe_US_curated.csv"
    target.write_text(
        "ticker,exchange,source_marker\nAAPL,NasdaqGS,sample_only_not_real_data\n",
        encoding="utf-8",
    )
    registry = tmp_path / "source_registry.yaml"
    registry.write_text(
        f"""
metadata:
  version: test
sources:
  - id: universe_us_curated
    source_type: versioned_csv
    status: real_curated
    required_for_internal_daily_run: true
    required_for_production_real_data: true
    replacement_target_path: {target.as_posix()}
""",
        encoding="utf-8",
    )
    rep = validate_source_registry(registry, require_production=True).as_dict()
    assert rep["status"] == "NOT_READY"
    assert rep["sources"][0]["file_exists"] is True
    assert rep["sources"][0]["file_contains_template_marker"] is True
    assert rep["sources"][0]["ready"] is False


def test_real_source_registry_accepts_marker_free_curated_target_file(tmp_path):
    target = tmp_path / "bond_yields_10y_curated.csv"
    target.write_text(
        "country,date,yield_10y,source,source_as_of\nUS,2026-07-08,0.044,official_export,2026-07-08\n",
        encoding="utf-8",
    )
    registry = tmp_path / "source_registry.yaml"
    registry.write_text(
        f"""
metadata:
  version: test
sources:
  - id: bond_10y_5y_avg_curated
    source_type: versioned_csv
    status: real_curated
    required_for_internal_daily_run: true
    required_for_production_real_data: true
    replacement_target_path: {target.as_posix()}
""",
        encoding="utf-8",
    )
    rep = validate_source_registry(registry, require_production=True).as_dict()
    assert rep["status"] == "PASS"
    assert rep["sources"][0]["file_contains_template_marker"] is False
    assert rep["sources"][0]["ready"] is True
