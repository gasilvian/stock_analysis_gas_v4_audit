from sws_engine.contracts.schema_validator import load_schema
from sws_engine.core.result import CONTRACT_FIELDS


def test_output_schema_required_fields(schema_path):
    schema = load_schema(schema_path)
    required = set(schema["required"])
    assert {"ticker", "exchange", "valuation_date", "provider_profile",
            "valuation_model", "valuation_variant", "scores", "checks",
            "lineage", "warnings"} <= required


def test_all_30_checks_return_contract_fields(run, demo_payload):
    out = run(demo_payload)
    assert len(out["checks"]) == 30
    for check in out["checks"]:
        for f in CONTRACT_FIELDS:
            assert f in check, f"check {check.get('name')} missing {f}"
        assert check["result"] in ("PASS", "FAIL", "UNKNOWN")
        assert check["source_quality"] in ("exact", "approximation",
                                           "assumption", "missing")
        assert check["source_class"] in ("E0", "E1", "E2", "E3", "E4")
    axes = {c["axis"] for c in out["checks"]}
    assert axes == {"value", "future", "past", "health", "dividend"}
    for axis in axes:
        assert sum(1 for c in out["checks"] if c["axis"] == axis) == 6
