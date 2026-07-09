import json
from pathlib import Path

from sws_engine.audit.model_applicability import assess_model_applicability


def _output():
    return json.loads(Path("examples/demo_output.json").read_text(encoding="utf-8"))


def test_model_applicability_identifier_master_takes_precedence():
    out = _output()
    out["ticker"] = "JPM"
    audit = assess_model_applicability(
        out,
        input_payload={"company_type": "non_financial", "industry": "Software"},
        identifier_master_records=[{
            "ticker": "JPM",
            "exchange": out.get("exchange"),
            "company_type": "bank",
            "security_type": "common",
            "industry": "Banks",
        }],
    )
    assert audit["identifier_master_used"] is True
    assert audit["company_type_detected"] == "bank"
    assert audit["status"] == "DEGRADED"
    assert audit["allowed_score_usage"] == "do_not_compare"


def test_model_applicability_adr_and_pharma_degrade_usage():
    out = _output()
    adr = assess_model_applicability(out, input_payload={"security_type": "ADR", "industry": "Foreign Issuer ADR"})
    assert adr["company_type_detected"] == "adr_foreign"
    assert adr["allowed_score_usage"] == "audit_only"
    pharma = assess_model_applicability(out, input_payload={"company_type": "pharma", "industry": "Biotechnology"})
    assert pharma["company_type_detected"] == "pharma"
    assert pharma["status"] == "DEGRADED"
    assert pharma["allowed_score_usage"] == "display_only"
