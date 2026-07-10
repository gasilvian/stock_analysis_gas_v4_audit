"""P2.3-enf tests: runtime TTL/staleness enforcement for curated injections.

Follow-up-audit gap: static validators checked expires_at and the registry
declared ttl_days, but injections never compared observation age with the TTL
at runtime. These tests pin: visible staleness (warning + lineage stamp,
value still injected), ERP expiry refusal, honest no-verdict when the
freshness contract is undeclared, and the live behavior on the repo's real
curated files.
"""
import json
from pathlib import Path

from sws_engine.rates.injection import build_curated_rates_overrides
from sws_engine.sources.staleness import staleness_check, ttl_days_for_source

ROOT = Path(__file__).resolve().parents[2]
BOND = str(ROOT / "data/real_sources/rates/bond_yields_10y_curated.csv")
ERP = str(ROOT / "data/real_sources/rates/erp_curated.json")


def test_registry_ttls_resolve():
    assert ttl_days_for_source("bond_10y_5y_avg_curated", ROOT / "config/source_registry.yaml") == 45
    assert ttl_days_for_source("erp_curated", ROOT / "config/source_registry.yaml") == 183
    assert ttl_days_for_source("nonexistent_source", ROOT / "config/source_registry.yaml") is None


def test_staleness_check_verdicts():
    fresh = staleness_check("2026-07-01", source_id="x", valuation_date="2026-07-10", ttl_days=45)
    assert fresh["stale"] is False and fresh["age_days"] == 9
    stale = staleness_check("2026-01-01", source_id="bond_10y_5y_avg_curated",
                            valuation_date="2026-07-10", ttl_days=45)
    assert stale["stale"] is True and stale["age_days"] == 190
    assert "CURATED_SOURCE_STALE" in stale["warning"]
    # no declared TTL / unknown as_of -> never invents staleness
    assert staleness_check("2020-01-01", source_id="x", valuation_date="2026-07-10", ttl_days=None)["stale"] is False
    assert staleness_check(None, source_id="x", valuation_date="2026-07-10", ttl_days=7)["stale"] is False


def test_fresh_bond_injects_without_stale_warning():
    inj = build_curated_rates_overrides(BOND, ERP, country="US", valuation_date="2026-07-10")
    assert "risk_free_rate_10y_5y_avg" in inj["overrides"]
    assert not any("CURATED_SOURCE_STALE" in w for w in inj["warnings"])
    assert "stale" not in inj["overrides"]["risk_free_rate_10y_5y_avg"]


def test_stale_bond_injects_with_visible_degradation():
    """Newest bond observation is 2026-07-08; at a valuation date 60 days
    later the 45-day TTL is exceeded: the value is STILL injected (an old
    official observation beats an invented one) but staleness is stamped in
    lineage and warned."""
    inj = build_curated_rates_overrides(BOND, ERP, country="US", valuation_date="2026-09-15")
    spec = inj["overrides"]["risk_free_rate_10y_5y_avg"]
    assert spec["value"] is not None
    assert spec["stale"] is True
    assert spec["stale_age_days"] > 45
    assert any("CURATED_SOURCE_STALE: bond_10y_5y_avg_curated" in w for w in inj["warnings"])


def test_expired_erp_is_refused_not_injected():
    """ERP expires 2027-01-15; past that date injection is refused (expiry is
    a curation contract) and the field stays honestly MISSING."""
    inj = build_curated_rates_overrides(BOND, ERP, country="US", valuation_date="2027-02-01")
    assert "equity_risk_premium" not in inj["overrides"]
    assert any(w.startswith("CURATED_ERP_EXPIRED") for w in inj["warnings"])


def test_stale_averages_snapshot_warns_and_stamps_lineage():
    from sws_engine.averages.injection import apply_averages_snapshot
    snap = json.loads((ROOT / "data/averages/averages_US-SYN_2026-07-06.json").read_text(encoding="utf-8"))
    snap["meta"]["source"] = "yfinance_universe_curated"
    snap["meta"]["industry_averages_as_of"] = "2025-12-01"  # far past default 90d
    payload = {"ticker": "T1", "industry": "Software", "valuation_date": "2026-07-10"}
    report = apply_averages_snapshot(payload, snap)
    assert "market_averages" in report["applied_fields"]
    assert any("CURATED_SOURCE_STALE" in w for w in payload["builder_warnings"])
    assert payload["lineage"]["field_lineage"]["market_averages"]["stale"] is True


def test_fresh_averages_snapshot_has_no_stale_stamp():
    from sws_engine.averages.injection import apply_averages_snapshot
    snap = json.loads((ROOT / "data/averages/averages_US-SYN_2026-07-06.json").read_text(encoding="utf-8"))
    snap["meta"]["source"] = "yfinance_universe_curated"
    payload = {"ticker": "T1", "industry": "Software", "valuation_date": "2026-07-10"}
    apply_averages_snapshot(payload, snap)
    assert "stale" not in payload["lineage"]["field_lineage"]["market_averages"]
