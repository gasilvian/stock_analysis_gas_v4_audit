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

# Debt is resolved semantically, not by FIELD_TAGS first-match order. ``Debt``
# is the declared US-GAAP total-debt aggregate. LongTermDebt already includes
# its current and noncurrent portions, so those portions are only a fallback.
TOTAL_DEBT_AGGREGATE_TAGS = ["Debt"]
SHORT_TERM_DEBT_AGGREGATE_TAGS = ["ShortTermBorrowings"]
SHORT_TERM_DEBT_COMPONENT_TAGS = ["CommercialPaper"]


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
    components: tuple["FactValue", ...] = ()
    transform: str | None = None

    @property
    def is_missing(self) -> bool:
        return self.value is None

    def as_dict(self) -> dict[str, Any]:
        result = {
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
        if self.transform:
            result["transform"] = self.transform
        if self.components:
            result["components"] = [component.as_dict() for component in self.components]
        return result


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


def _same_reporting_context(left: FactValue, right: FactValue) -> bool:
    """Require debt components to describe the same filing period."""
    return (
        left.unit == right.unit
        and left.fiscal_year == right.fiscal_year
        and left.fiscal_period == right.fiscal_period
        and left.end == right.end
    )


def _annual_fact_candidates(
    facts_json: dict[str, Any], field: str, tag: str
) -> list[FactValue]:
    """Return every eligible annual observation for one explicit tag.

    This is intentionally separate from ``latest_fact``: semantic resolvers
    need to search older compatible contexts without changing generic field
    selection behavior.
    """
    tag_obj = _facts(facts_json).get(tag) or {}
    candidates: list[FactValue] = []
    for unit, item in _unit_items(tag_obj):
        if item.get("val") is None or not _form_ok(item, annual=True):
            continue
        candidates.append(
            FactValue(
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
        )
    return sorted(
        candidates,
        key=lambda fact: (
            fact.fiscal_year or -9999,
            fact.end or "",
            fact.filed or "",
        ),
        reverse=True,
    )


def _matching_candidate(
    candidates: list[FactValue], anchor: FactValue
) -> FactValue | None:
    return next(
        (candidate for candidate in candidates if _same_reporting_context(anchor, candidate)),
        None,
    )


def _components_with_short_term(
    base: list[FactValue],
    short_term_borrowings: list[FactValue],
    commercial_paper: list[FactValue],
) -> list[FactValue] | None:
    anchor = base[0]
    short_term = _matching_candidate(short_term_borrowings, anchor)
    if short_term is None:
        short_term = _matching_candidate(commercial_paper, anchor)
    if short_term is not None:
        return [*base, short_term]
    if short_term_borrowings or commercial_paper:
        return None
    return base


def _direct_total_debt(aggregate: FactValue) -> FactValue:
    return FactValue(
        field="total_debt",
        tag=aggregate.tag,
        value=aggregate.value,
        unit=aggregate.unit,
        fiscal_year=aggregate.fiscal_year,
        fiscal_period=aggregate.fiscal_period,
        form=aggregate.form,
        filed=aggregate.filed,
        end=aggregate.end,
        frame=aggregate.frame,
        reason_code="TOTAL_DEBT_DIRECT_AGGREGATE",
        components=(aggregate,),
        transform="direct_declared_total_debt_aggregate",
    )


def _derived_total_debt(components: list[FactValue]) -> FactValue:
    anchor = components[0]
    return FactValue(
        field="total_debt",
        tag=None,
        value=sum(float(component.value) for component in components if component.value is not None),
        unit=anchor.unit,
        fiscal_year=anchor.fiscal_year,
        fiscal_period=anchor.fiscal_period,
        form=anchor.form,
        filed=max((component.filed or "" for component in components), default=None) or None,
        end=anchor.end,
        frame=anchor.frame,
        reason_code="TOTAL_DEBT_DERIVED_FROM_DECLARED_COMPONENTS",
        components=tuple(components),
        transform="sum_declared_debt_components",
    )


def total_debt_fact(facts_json: dict[str, Any]) -> FactValue:
    """Resolve balance-sheet total debt without partial-tag mislabelling.

    A declared ``Debt`` aggregate wins. Otherwise LongTermDebt is combined
    with a separately reported short-term aggregate, or with declared
    CommercialPaper when no short-term aggregate exists. If LongTermDebt is
    absent, its current and noncurrent portions must both exist. Finance lease
    liabilities, cash-flow debt tags and undocumented carrying amounts are
    deliberately outside this mapping.
    """
    aggregates = _annual_fact_candidates(facts_json, "total_debt", "Debt")
    if aggregates:
        return _direct_total_debt(aggregates[0])

    long_term = _annual_fact_candidates(
        facts_json, "LongTermDebt", "LongTermDebt"
    )
    current = _annual_fact_candidates(
        facts_json, "LongTermDebtCurrent", "LongTermDebtCurrent"
    )
    noncurrent = _annual_fact_candidates(
        facts_json, "LongTermDebtNoncurrent", "LongTermDebtNoncurrent"
    )
    short_term = _annual_fact_candidates(
        facts_json, "ShortTermBorrowings", "ShortTermBorrowings"
    )
    commercial_paper = _annual_fact_candidates(
        facts_json, "CommercialPaper", "CommercialPaper"
    )

    for candidate in long_term:
        components = _components_with_short_term(
            [candidate], short_term, commercial_paper
        )
        if components is not None:
            return _derived_total_debt(components)

    for current_candidate in current:
        noncurrent_candidate = _matching_candidate(noncurrent, current_candidate)
        if noncurrent_candidate is None:
            continue
        components = _components_with_short_term(
            [current_candidate, noncurrent_candidate],
            short_term,
            commercial_paper,
        )
        if components is not None:
            return _derived_total_debt(components)

    reason_code = (
        "XBRL_TOTAL_DEBT_COMPATIBLE_CONTEXT_MISSING"
        if long_term or (current and noncurrent)
        else "XBRL_TOTAL_DEBT_VALID_CONSTRUCTION_MISSING"
    )
    return FactValue(
        field="total_debt", tag=None, value=None, unit=None,
        fiscal_year=None, fiscal_period=None, form=None, filed=None,
        end=None, frame=None, reason_code=reason_code,
    )


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
