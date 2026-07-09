"""Payload builder (Phase 3): assembles a full engine payload from
(1) a recorded provider snapshot, (2) an averages snapshot,
(3) the rates layer. Strict mode preserved: nothing is invented; missing
fields stay missing and degrade to UNKNOWN downstream.

For loss-making companies it derives the cash-runway inputs from the
recorded free-cash-flow history (SPEC 5.5 data points), which is a
mechanical derivation, not an invented value."""
from sws_engine.providers.recorded import RecordedProvider
from sws_engine.rates.rates import bond_10y_5y_average, load_erp


def burn_inputs_from_snapshot(payload: dict) -> dict:
    """Levered FCF (1y) and 3y burn growth from OCF/capex history if the
    company burns cash; returns {} otherwise."""
    ocf = payload.get("operating_cash_flow")
    capex = payload.get("capex_history_3y") or []
    if ocf is None or not capex:
        return {}
    fcf_now = ocf - abs(capex[-1])
    if fcf_now >= 0:
        return {}
    out = {"annual_free_cash_burn": -fcf_now}
    # burn growth: compare implied burn using oldest vs latest capex year
    # only when OCF history is unavailable we approximate growth via capex
    hist = payload.get("fcf_history")
    if hist and len(hist) >= 3 and hist[0] < 0 and hist[-1] < 0:
        b0, b1 = -hist[0], -hist[-1]
        years = len(hist) - 1
        out["cash_burn_growth_3y"] = (b1 / b0) ** (1 / years) - 1
    return out


def build_company_payload(*, snapshot_path: str, averages_snapshot: dict,
                          industry: str, country: str, valuation_date: str,
                          bond_csv: str, erp_json: str,
                          overrides: dict = None):
    """Returns (payload, provider_result) ready for run_company_analysis."""
    provider = RecordedProvider(snapshot_path)
    pr = provider.prepare(payload_overrides={"valuation_date": valuation_date})
    payload = pr.payload

    mk = dict(averages_snapshot["market"])
    ind = dict(averages_snapshot["industries"].get(industry) or {})
    payload["market_averages"] = mk
    payload["industry_averages"] = ind
    payload["lineage"]["industry_averages_as_of"] = \
        averages_snapshot["meta"]["industry_averages_as_of"]
    for w in averages_snapshot.get("warnings", []):
        pr.degradations.append(w)
    if averages_snapshot["meta"].get("source") == "synthetic_curated":
        pr.degradations.append(
            "SYNTHETIC_CURATED_DATA: industry/market averages built from a "
            "synthetic universe for construction/testing")
    pr.field_quality["market_averages"] = "approximation"
    pr.field_quality["industry_averages"] = "approximation"

    rf = bond_10y_5y_average(bond_csv, country, valuation_date)
    erp = load_erp(erp_json, country)
    if rf["value"] is not None:
        payload["risk_free_rate_10y_5y_avg"] = rf["value"]
        pr.field_quality["risk_free_rate_10y_5y_avg"] = "assumption"
    if erp["value"] is not None:
        payload["equity_risk_premium"] = erp["value"]
        pr.field_quality["equity_risk_premium"] = "assumption"
        pr.degradations.append(
            "ASSUMPTION_USED: equity risk premium from curated table "
            f"({erp.get('source', 'n/a')})")

    payload.update(burn_inputs_from_snapshot(payload))
    payload.update(overrides or {})
    # embed builder-level degradations so they survive into the final output
    payload["builder_warnings"] = list(dict.fromkeys(pr.degradations))
    return payload, pr
