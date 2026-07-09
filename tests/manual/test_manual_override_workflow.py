import json
from pathlib import Path

from sws_engine.manual.overrides import dry_run_report, load_override_file, merge_overrides


def test_manual_override_merge_adds_lineage(tmp_path):
    base = {"ticker": "X", "provider_profile": "yfinance_pragmatic", "lineage": {"field_lineage": {}}, "builder_warnings": []}
    override = {"fields": {"market_averages": {"value": {"pe_median_profitable": 20}, "source_quality": "exact", "source_class": "E3"}}}
    merged, report = merge_overrides(base, [override])
    assert report.applied_fields == ["market_averages"]
    assert merged["market_averages"]["pe_median_profitable"] == 20
    assert merged["lineage"]["field_lineage"]["market_averages"]["provider"] == "manual_override"
    assert any("MANUAL_OVERRIDE_USED" in w for w in merged["builder_warnings"])


def test_dry_run_reports_impacted_checks():
    payload = {"ticker": "X", "provider_profile": "yfinance_pragmatic", "price": 10}
    report = dry_run_report(payload)
    assert "missing_fields" in report
    assert "impacted_checks_likely_unknown" in report
    assert any(k.startswith("V") for k in report["impacted_checks_likely_unknown"])


def test_override_templates_exist_and_load():
    for path in [
        "templates/company_input_template.json",
        "templates/bank_input_template.json",
        "templates/reit_input_template.json",
        "templates/manual_override_template.json",
        "templates/bank_manual_override_template.json",
        "templates/reit_manual_override_template.json",
    ]:
        assert Path(path).exists(), path
        with open(path, "r", encoding="utf-8") as fh:
            assert isinstance(json.load(fh), dict)
