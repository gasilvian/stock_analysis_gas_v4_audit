"""Normalize a minimal SEC CompanyFacts statement snapshot.

P0.3 maps only declared fields needed by the existing v3.1 engine and audit
layer. Missing tags remain UNKNOWN in the mapping report; no defaults are used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sws_engine.core.enums import ProviderProfile, SourceClass, SourceQuality
from sws_engine.sec.cik_resolver import CikRecord
from sws_engine.sec.xbrl_tag_resolver import FactValue, annual_series, intangible_assets, latest_fact

PROVIDER_ID = "sec_companyfacts"

SNAPSHOT_FIELDS = [
    "revenue",
    "gross_profit",
    "operating_income",
    "ebit",
    "net_income",
    "total_assets",
    "total_liabilities",
    "equity",
    "cash_and_st_investments",
    "cash",
    "total_debt",
    "intangible_assets",
    "operating_cash_flow",
    "dividends_paid",
    "shares_outstanding",
    "eps",
    "interest_expense",
    "bank_deposits",
    "allowance_for_credit_losses",
]

PAYLOAD_FIELD_ALIASES = {
    "interest_expense": "net_interest_expense",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _lineage_for(fact: FactValue, *, cik: str, source_path: str) -> dict[str, Any]:
    return {
        "source_id": PROVIDER_ID,
        "provider": PROVIDER_ID,
        "source_field": f"us-gaap:{fact.tag}" if fact.tag else None,
        "source_quality": SourceQuality.EXACT.value if fact.value is not None else SourceQuality.MISSING.value,
        "source_class": SourceClass.E0.value,
        "tier": "official_filing",
        "as_of": fact.filed or fact.end,
        "fiscal_year": fact.fiscal_year,
        "fiscal_period": fact.fiscal_period,
        "form": fact.form,
        "unit": fact.unit,
        "cik": cik,
        "source_path": source_path,
        "reason_code": fact.reason_code,
    }


def normalize_capex_series(facts_json: dict[str, Any]) -> tuple[list[float], list[dict[str, Any]]]:
    facts = annual_series(facts_json, "capex", max_items=3)
    values: list[float] = []
    lineage: list[dict[str, Any]] = []
    for fact in facts:
        if fact.value is None:
            continue
        values.append(abs(float(fact.value)))
        lineage.append(fact.as_dict())
    return values, lineage


def build_statement_snapshot(
    facts_json: dict[str, Any],
    *,
    cik_record: CikRecord,
    source_path: str,
    valuation_date: str | None = None,
) -> dict[str, Any]:
    cik = cik_record.cik10
    fields: dict[str, dict[str, Any]] = {}
    payload_updates: dict[str, Any] = {
        "ticker": cik_record.ticker,
        "provider_profile": ProviderProfile.SWS_PUBLIC_FAITHFUL_MANUAL_INPUTS.value,
    }
    if valuation_date:
        payload_updates["valuation_date"] = valuation_date
    if cik_record.exchange:
        payload_updates["exchange"] = cik_record.exchange
    payload_lineage: dict[str, Any] = {}
    mapped: list[str] = []
    unmapped: list[dict[str, str]] = []

    for field in SNAPSHOT_FIELDS:
        fact = intangible_assets(facts_json) if field == "intangible_assets" else latest_fact(facts_json, field)
        fields[field] = fact.as_dict()
        target_field = PAYLOAD_FIELD_ALIASES.get(field, field)
        payload_lineage[target_field] = _lineage_for(fact, cik=cik, source_path=source_path)
        if fact.value is None:
            unmapped.append({"field": field, "reason_code": fact.reason_code})
            continue
        value = float(fact.value)
        if field == "interest_expense":
            value = abs(value)
        payload_updates[target_field] = value
        mapped.append(field)

    capex_values, capex_lineage = normalize_capex_series(facts_json)
    if capex_values:
        payload_updates["capex_history_3y"] = capex_values
        mapped.append("capex_history_3y")
        payload_lineage["capex_history_3y"] = {
            "source_id": PROVIDER_ID,
            "provider": PROVIDER_ID,
            "source_field": "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "source_quality": SourceQuality.EXACT.value,
            "source_class": SourceClass.E0.value,
            "tier": "official_filing",
            "as_of": capex_lineage[-1].get("filed") if capex_lineage else None,
            "transform": "absolute_outflow_last_3y",
            "cik": cik,
            "source_path": source_path,
        }
    else:
        unmapped.append({"field": "capex_history_3y", "reason_code": "XBRL_TAG_MISSING"})
        payload_lineage["capex_history_3y"] = {
            "source_id": PROVIDER_ID,
            "provider": PROVIDER_ID,
            "source_field": "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "source_quality": SourceQuality.MISSING.value,
            "source_class": SourceClass.E0.value,
            "tier": "official_filing",
            "reason_code": "XBRL_TAG_MISSING",
            "cik": cik,
            "source_path": source_path,
        }

    payload_updates.setdefault("lineage", {})["field_lineage"] = payload_lineage
    payload_updates["lineage"]["sec_companyfacts_cik"] = cik
    payload_updates["lineage"]["sec_companyfacts_source"] = source_path
    payload_updates["lineage"]["sec_companyfacts_normalized_at"] = utc_now()
    payload_updates["sec_mapping_warnings"] = [f"{u['field']}:{u['reason_code']}" for u in unmapped]

    status = "PASS_WITH_LIMITATIONS" if mapped else "UNKNOWN"
    return {
        "status": status,
        "ticker": cik_record.ticker,
        "cik": cik,
        "source_path": source_path,
        "normalized_at": payload_updates["lineage"]["sec_companyfacts_normalized_at"],
        "valuation_date": valuation_date,
        "fields": fields,
        "capex_history_3y": capex_values,
        "payload_updates": payload_updates,
        "mapping_report": {
            "status": status,
            "mapped_fields": sorted(set(mapped)),
            "unmapped_fields": unmapped,
            "source_quality": SourceQuality.EXACT.value,
            "source_class": SourceClass.E0.value,
            "source_tier": "official_filing",
            "unknown_policy": "missing tags remain UNKNOWN; no substitute tags are inferred",
        },
    }
