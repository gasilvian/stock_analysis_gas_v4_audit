import copy
import json
from pathlib import Path

from sws_engine.audit.data_confidence import assess_data_confidence
from sws_engine.audit.policies import load_audit_policies, load_source_registry


def _demo_output():
    return json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))


def test_data_confidence_uses_field_lineage_and_source_tiers():
    out = _demo_output()
    payload = {
        "provider_profile": out["provider_profile"],
        "lineage": {
            "field_lineage": {
                "revenue": {"source_id": "sec_companyfacts", "source_quality": "exact", "as_of": "2026-07-01"},
                "price": {"source_id": "yfinance_equity_live", "source_quality": "approximation", "as_of": "2026-07-01"},
            }
        },
    }
    registry = load_source_registry()
    registry.setdefault("sources", []).append({"id": "sec_companyfacts", "tier": "official_filing", "source_quality_default": "exact", "ttl_days": 120})
    audit = assess_data_confidence(out, input_payload=payload, source_registry=registry)
    assert audit["field_lineage_score"] > 0
    assert audit["source_tier_mix"]["official_filing"] == 1
    assert audit["source_tier_mix"]["pragmatic"] == 1
    assert audit["policy_version"] == "v4.0-p0.2"


def test_data_confidence_marks_stale_fields_without_hiding_unknowns():
    out = _demo_output()
    out = copy.deepcopy(out)
    out["checks"][0]["result"] = "UNKNOWN"
    out["checks"][0]["reason_code"] = "MISSING_FCF_ESTIMATES"
    out["checks"][0]["source_quality"] = "missing"
    payload = {
        "lineage": {
            "field_lineage": {
                "price": {"source_id": "yfinance_equity_live", "source_quality": "approximation", "as_of": "2000-01-01"}
            }
        }
    }
    audit = assess_data_confidence(out, input_payload=payload)
    assert audit["unknown_checks_count"] == 1
    assert audit["stale_fields"]
    assert "STALE_FIELDS_PRESENT" in audit["reason_codes"]


def test_audit_policies_are_separate_from_model_assumptions():
    policies = load_audit_policies()
    assert policies["metadata"]["version"] == "v4.0-p0.2"
    assert "data_confidence" in policies
    assert "dcf_decay_factor" not in policies
