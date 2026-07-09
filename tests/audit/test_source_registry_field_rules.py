from sws_engine.audit.policies import field_rules_index, load_source_registry, source_registry_index


def test_source_registry_has_p0_2_audit_metadata():
    registry = load_source_registry()
    by_id = source_registry_index(registry)
    assert by_id["yfinance_equity_live"]["tier"] == "pragmatic"
    assert by_id["yfinance_equity_live"]["field_quality_caps"]["*"] == "approximation"
    assert by_id["erp_curated"]["tier"] == "manual"
    rules = field_rules_index(registry)
    assert rules["intangible_assets"]["conflict_policy"] == "report_and_unknown"
    assert "yfinance_equity_live" in rules["intangible_assets"]["disallowed_as_official"]
