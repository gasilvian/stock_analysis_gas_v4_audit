"""Small, explicit XBRL tag resolver for SEC CompanyFacts.

The resolver only maps declared candidate tags. If none exists, the field is
UNKNOWN. It never substitutes an undeclared "close" tag.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A"}
QUARTERLY_FORMS = {"10-Q", "10-Q/A"}

FIELD_TAGS: dict[str, list[str]] = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "ebit": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash_and_st_investments": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "total_debt": ["LongTermDebtAndFinanceLeaseObligations", "LongTermDebtAndFinanceLeaseObligationsCurrent", "LongTermDebtCurrent"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "shares_outstanding": ["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"],
    "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "interest_expense": ["InterestExpenseNonOperating", "InterestExpense"],
    # bank-specific foundation; not all are used by standard engine yet.
    "bank_deposits": ["Deposits", "DepositsLiabilities"],
    "allowance_for_credit_losses": ["AllowanceForCreditLosses", "FinancingReceivableAllowanceForCreditLosses"],
}

INTANGIBLE_COMPONENT_TAGS = ["IntangibleAssetsNetExcludingGoodwill", "Goodwill"]


@dataclass(frozen=True)
class FactValue:
    field: str
    tag: str | None
    value: float | int | None
    unit: str | None
    fiscal_year: int | None
    fiscal_period: str | None
    form: str | None
    filed: str | None
    end: str | None
    frame: str | None
    reason_code: str = "OK"

    @property
    def is_missing(self) -> bool:
        return self.value is None

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "tag": self.tag,
            "value": self.value,
            "unit": self.unit,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period,
            "form": self.form,
            "filed": self.filed,
            "end": self.end,
            "frame": self.frame,
            "reason_code": self.reason_code,
        }


def _facts(facts_json: dict[str, Any]) -> dict[str, Any]:
    return ((facts_json.get("facts") or {}).get("us-gaap") or {})


def _unit_items(tag_obj: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    units = tag_obj.get("units") or {}
    preferred = ["USD", "USD/shares", "shares", "pure"]
    emitted: set[str] = set()
    for unit in preferred:
        for item in units.get(unit, []) or []:
            emitted.add(unit)
            yield unit, item
    for unit, items in units.items():
        if unit in emitted:
            continue
        for item in items or []:
            yield unit, item


def _form_ok(item: dict[str, Any], *, annual: bool) -> bool:
    form = str(item.get("form") or "")
    return form in (ANNUAL_FORMS if annual else ANNUAL_FORMS | QUARTERLY_FORMS)


def _fy_fp_sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
    fy = item.get("fy")
    try:
        fy_int = int(fy)
    except (TypeError, ValueError):
        fy_int = -9999
    return (fy_int, str(item.get("filed") or ""), str(item.get("end") or ""))


def _select_latest(tag_obj: dict[str, Any], *, annual: bool = True) -> tuple[str, dict[str, Any]] | None:
    candidates = [(unit, item) for unit, item in _unit_items(tag_obj) if item.get("val") is not None and _form_ok(item, annual=annual)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda ui: _fy_fp_sort_key(ui[1]))[-1]


def latest_fact(
    facts_json: dict[str, Any],
    field: str,
    *,
    tags: list[str] | None = None,
    annual: bool = True,
) -> FactValue:
    us_gaap = _facts(facts_json)
    for tag in tags or FIELD_TAGS.get(field, []):
        tag_obj = us_gaap.get(tag)
        if not tag_obj:
            continue
        selected = _select_latest(tag_obj, annual=annual)
        if not selected:
            continue
        unit, item = selected
        return FactValue(
            field=field,
            tag=tag,
            value=item.get("val"),
            unit=unit,
            fiscal_year=item.get("fy"),
            fiscal_period=item.get("fp"),
            form=item.get("form"),
            filed=item.get("filed"),
            end=item.get("end"),
            frame=item.get("frame"),
        )
    return FactValue(field=field, tag=None, value=None, unit=None, fiscal_year=None, fiscal_period=None, form=None, filed=None, end=None, frame=None, reason_code="XBRL_TAG_MISSING")


def annual_series(
    facts_json: dict[str, Any],
    field: str,
    *,
    tags: list[str] | None = None,
    max_items: int = 3,
) -> list[FactValue]:
    us_gaap = _facts(facts_json)
    for tag in tags or FIELD_TAGS.get(field, []):
        tag_obj = us_gaap.get(tag)
        if not tag_obj:
            continue
        candidates = [(unit, item) for unit, item in _unit_items(tag_obj) if item.get("val") is not None and _form_ok(item, annual=True)]
        if not candidates:
            continue
        # Deduplicate by fiscal year, keep latest filed for that year.
        by_year: dict[int, tuple[str, dict[str, Any]]] = {}
        for unit, item in candidates:
            try:
                fy = int(item.get("fy"))
            except (TypeError, ValueError):
                continue
            if fy not in by_year or _fy_fp_sort_key(item) > _fy_fp_sort_key(by_year[fy][1]):
                by_year[fy] = (unit, item)
        out: list[FactValue] = []
        for fy in sorted(by_year)[-max_items:]:
            unit, item = by_year[fy]
            out.append(FactValue(field=field, tag=tag, value=item.get("val"), unit=unit, fiscal_year=fy, fiscal_period=item.get("fp"), form=item.get("form"), filed=item.get("filed"), end=item.get("end"), frame=item.get("frame")))
        if out:
            return out
    return []


def intangible_assets(facts_json: dict[str, Any]) -> FactValue:
    parts: list[FactValue] = [latest_fact(facts_json, tag, tags=[tag]) for tag in INTANGIBLE_COMPONENT_TAGS]
    present = [p for p in parts if not p.is_missing]
    if not present:
        return FactValue(field="intangible_assets", tag="+".join(INTANGIBLE_COMPONENT_TAGS), value=None, unit=None, fiscal_year=None, fiscal_period=None, form=None, filed=None, end=None, frame=None, reason_code="XBRL_TAG_MISSING")
    value = sum(float(p.value or 0.0) for p in present)
    latest = sorted(present, key=lambda p: (p.fiscal_year or -9999, p.filed or ""))[-1]
    return FactValue(field="intangible_assets", tag="+".join(p.tag or "" for p in present), value=value, unit=latest.unit, fiscal_year=latest.fiscal_year, fiscal_period=latest.fiscal_period, form=latest.form, filed=latest.filed, end=latest.end, frame=latest.frame)
