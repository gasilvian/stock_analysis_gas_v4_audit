"""B5 tests: source conflict detector — registry precedence and UNKNOWN doctrine.

Pins the doctrine-critical behavior: conflicts between sources resolve ONLY
through the registry precedence chain; a pair not covered by the chain makes
the field UNKNOWN — never a silent pick. Also pins the standalone
conflict-report artifact and its materiality flagging.
"""
import json
from pathlib import Path

from sws_engine.sources.conflict_detector import (
    build_conflict_report,
    load_precedence,
    resolve_field,
    resolve_precedence,
    write_conflict_report,
)

ROOT = Path(__file__).resolve().parents[2]


def test_registry_precedence_chain_loads():
    chain = load_precedence(ROOT / "config/source_registry.yaml")
    assert chain[0] == "manual_override"
    assert chain.index("sec_companyfacts") < chain.index("yfinance")
    assert chain.index("manual_estimates_pack") < chain.index("sec_companyfacts")


def test_resolve_precedence_and_unknown_for_uncovered_pair():
    chain = ["manual_override", "sec_companyfacts", "yfinance"]
    assert resolve_precedence("sec_companyfacts", "yfinance", chain) == "sec_companyfacts"
    assert resolve_precedence("yfinance", "manual_override", chain) == "manual_override"
    # yfinance_pragmatic normalizes to yfinance
    assert resolve_precedence("sec_companyfacts", "yfinance_pragmatic", chain) == "sec_companyfacts"
    # a source outside the chain -> no rule -> None
    assert resolve_precedence("sec_companyfacts", "mystery_feed", chain) is None


def test_resolve_field_unresolved_pair_yields_unknown_not_a_pick():
    result = resolve_field("revenue", {
        "sec_companyfacts": {"value": 391e9},
        "mystery_feed": {"value": 410e9},
    }, precedence=["manual_override", "sec_companyfacts", "yfinance"])
    assert result["status"] == "UNKNOWN"
    assert result["value"] is None
    assert result["winner"] is None
    assert result["reason_code"] == "SOURCE_CONFLICT_UNRESOLVED"
    assert result["conflicts"][0]["resolution"] == "unresolved_no_precedence_rule"


def test_resolve_field_precedence_and_materiality():
    result = resolve_field("revenue", {
        "yfinance": {"value": 410e9},
        "sec_companyfacts": {"value": 391e9},
    }, precedence=["sec_companyfacts", "yfinance"], material_threshold=0.03)
    assert result["status"] == "RESOLVED"
    assert result["winner"] == "sec_companyfacts"
    assert result["value"] == 391e9
    conflict = result["conflicts"][0]
    assert conflict["resolution"] == "precedence:sec_companyfacts"
    assert conflict["material_review_required"] is True  # ~4.6% > 3%


def test_sec_merge_unresolved_provider_sets_field_unknown():
    """Doctrine wired into the SEC merge: when the base field's provider is
    not covered by the precedence chain, the conflicting field becomes None
    with SOURCE_CONFLICT_UNRESOLVED lineage instead of either value winning."""
    from sws_engine.sec.payload_merge import apply_sec_payload_updates
    payload = {
        "ticker": "AAPL", "provider_profile": "yfinance_pragmatic",
        "revenue": 410e9,
        "lineage": {"field_lineage": {
            "revenue": {"provider": "mystery_feed", "source_quality": "exact", "source_class": "E3"},
        }},
    }
    updates = {
        "ticker": "AAPL",
        "revenue": 391e9,
        "lineage": {"field_lineage": {
            "revenue": {"provider": "sec_companyfacts", "source_quality": "exact",
                        "source_class": "E0", "tier": "official_filing"},
        }},
    }
    report = apply_sec_payload_updates(payload, updates,
                                       precedence=["manual_override", "sec_companyfacts", "yfinance"])
    assert "revenue" in report["unresolved_fields"]
    assert payload["revenue"] is None
    lin = payload["lineage"]["field_lineage"]["revenue"]
    assert lin["reason_code"] == "SOURCE_CONFLICT_UNRESOLVED"
    assert lin["source_quality"] == "missing"
    assert payload["source_conflicts"][0]["resolution"] == "unresolved_no_precedence_rule"


def test_sec_merge_base_wins_when_registry_says_so():
    """A manual_override base value outranks SEC per the chain: SEC value is
    NOT applied, the conflict is still recorded transparently."""
    from sws_engine.sec.payload_merge import apply_sec_payload_updates
    payload = {
        "ticker": "AAPL", "provider_profile": "yfinance_pragmatic",
        "revenue": 400e9,
        "lineage": {"field_lineage": {
            "revenue": {"provider": "manual_override", "source_quality": "exact", "source_class": "E3"},
        }},
    }
    updates = {
        "ticker": "AAPL", "revenue": 391e9,
        "lineage": {"field_lineage": {
            "revenue": {"provider": "sec_companyfacts", "source_quality": "exact", "source_class": "E0"},
        }},
    }
    report = apply_sec_payload_updates(payload, updates)
    assert payload["revenue"] == 400e9
    assert payload["lineage"]["field_lineage"]["revenue"]["provider"] == "manual_override"
    assert report["conflicts"][0]["resolution"] == "precedence:manual_override"
    assert "revenue" not in report["applied_fields"]


def test_conflict_report_statuses_and_artifact(tmp_path):
    # no conflicts -> PASS
    clean = {"ticker": "T0", "valuation_date": "2026-07-10"}
    assert build_conflict_report(clean)["reason_code"] == "SOURCE_CONFLICTS_NONE"

    payload = {
        "ticker": "AAPL", "valuation_date": "2026-07-10",
        "provider_profile": "yfinance_pragmatic",
        "source_conflicts": [
            {"field": "revenue", "base_value": 410e9, "base_provider": "yfinance",
             "sec_value": 391e9, "relative_diff": 0.046256, "resolution": "sec_precedence"},
            {"field": "ebit", "base_value": 120e9, "base_provider": "yfinance",
             "sec_value": 123.2e9, "relative_diff": 0.026, "resolution": "sec_precedence"},
        ],
    }
    result = write_conflict_report(payload, tmp_path, material_threshold=0.03)
    report = result["report"]
    assert report["status"] == "PASS_WITH_LIMITATIONS"
    assert report["reason_code"] == "SOURCE_CONFLICT_MATERIAL_REVIEW_REQUIRED"
    assert report["conflicts_count"] == 2 and report["material_count"] == 1
    assert report["manual_review_required"] is True
    assert Path(result["paths"]["source_conflicts_json"]).exists()
    md = Path(result["paths"]["source_conflicts_report_md"]).read_text(encoding="utf-8")
    assert "revenue" in md and "YES" in md and "Not investment advice" in md

    # unresolved -> FAIL
    payload["source_conflicts"].append(
        {"field": "ebitda", "base_value": 1.0, "base_provider": "mystery_feed",
         "sec_value": 2.0, "relative_diff": 0.5, "resolution": "unresolved_no_precedence_rule"})
    assert build_conflict_report(payload)["status"] == "FAIL"


def test_cli_source_conflict_report_registers_artifact(tmp_path):
    from sws_engine.cli import main as cli_main
    from sws_engine.db.artifacts import latest_artifact
    payload = {
        "ticker": "AAPL", "valuation_date": "2026-07-10",
        "source_conflicts": [
            {"field": "revenue", "base_value": 410e9, "base_provider": "yfinance",
             "sec_value": 391e9, "relative_diff": 0.046256, "resolution": "sec_precedence"}],
    }
    payload_path = tmp_path / "AAPL_payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    db = tmp_path / "idx.db"
    rc = cli_main(["source-conflict-report", "--payload", str(payload_path),
                   "--output", str(tmp_path / "out"), "--db", str(db)])
    assert rc in (None, 0)
    found = latest_artifact(db, "AAPL", "source_conflicts_json")
    assert found and Path(found["path"]).exists()
