from sws_engine.sec.cik_resolver import CikRecord
from sws_engine.sec.statement_snapshot import build_statement_snapshot
from sws_engine.sec.xbrl_tag_resolver import total_debt_fact


def _observation(
    value,
    *,
    fy=2025,
    fp="FY",
    form="10-K",
    filed="2025-10-31",
    end="2025-09-27",
):
    return {
        "val": value,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
        "end": end,
        "frame": f"CY{fy}Q3I",
    }


def _fact(value, **context):
    return {"units": {"USD": [_observation(value, **context)]}}


def _fact_series(*observations):
    return {"units": {"USD": list(observations)}}


def _companyfacts(**tags):
    return {
        "facts": {
            "us-gaap": {
                tag: value if isinstance(value, dict) else _fact(value)
                for tag, value in tags.items()
            }
        }
    }


def test_total_debt_prefers_direct_declared_aggregate():
    fact = total_debt_fact(
        _companyfacts(
            Debt=100,
            LongTermDebt=90,
            LongTermDebtCurrent=10,
            LongTermDebtNoncurrent=80,
            CommercialPaper=7,
        )
    )
    assert fact.field == "total_debt"
    assert fact.tag == "Debt"
    assert fact.value == 100
    assert [part.tag for part in fact.components] == ["Debt"]
    assert fact.transform == "direct_declared_total_debt_aggregate"
    assert fact.reason_code == "TOTAL_DEBT_DIRECT_AGGREGATE"

    snapshot = build_statement_snapshot(
        _companyfacts(Debt=100),
        cik_record=CikRecord(ticker="TEST", cik="1", exchange="US"),
        source_path="direct.json",
    )
    lineage = snapshot["payload_updates"]["lineage"]["field_lineage"]["total_debt"]
    assert lineage["source_field"] == "us-gaap:Debt"
    assert lineage["component_source_fields"] == ["us-gaap:Debt"]
    assert lineage["reason_code"] == "TOTAL_DEBT_DIRECT_AGGREGATE"


def test_total_debt_uses_long_term_debt_plus_commercial_paper_without_double_counting():
    fact = total_debt_fact(
        _companyfacts(
            LongTermDebt=90,
            LongTermDebtCurrent=12,
            LongTermDebtNoncurrent=78,
            CommercialPaper=8,
        )
    )
    assert fact.tag is None
    assert fact.value == 98
    assert [part.tag for part in fact.components] == ["LongTermDebt", "CommercialPaper"]


def test_total_debt_falls_back_to_current_noncurrent_and_commercial_paper():
    fact = total_debt_fact(
        _companyfacts(
            LongTermDebtCurrent=12,
            LongTermDebtNoncurrent=78,
            CommercialPaper=8,
        )
    )
    assert fact.value == 98
    assert [part.tag for part in fact.components] == [
        "LongTermDebtCurrent",
        "LongTermDebtNoncurrent",
        "CommercialPaper",
    ]


def test_total_debt_missing_valid_construction_is_unknown_and_ignores_invalid_tags():
    fact = total_debt_fact(
        _companyfacts(
            LongTermDebtCurrent=12,
            ProceedsFromIssuanceOfLongTermDebt=50,
            RepaymentsOfLongTermDebt=20,
            DebtInstrumentCarryingAmount=70,
            FinanceLeaseLiability=5,
        )
    )
    assert fact.value is None
    assert fact.reason_code == "XBRL_TOTAL_DEBT_VALID_CONSTRUCTION_MISSING"


def test_total_debt_does_not_add_finance_lease_liability_automatically():
    fact = total_debt_fact(
        _companyfacts(LongTermDebt=90, CommercialPaper=8, FinanceLeaseLiability=5)
    )
    assert fact.value == 98
    assert "FinanceLeaseLiability" not in [part.tag for part in fact.components]


def test_total_debt_uses_same_context_commercial_paper_when_latest_short_term_is_incompatible():
    facts = _companyfacts(
        LongTermDebt=_fact(90, fy=2025),
        ShortTermBorrowings=_fact(
            6, fy=2024, filed="2024-10-31", end="2024-09-28"
        ),
        CommercialPaper=_fact(8, fy=2025),
    )
    fact = total_debt_fact(facts)
    assert fact.value == 98
    assert [part.tag for part in fact.components] == [
        "LongTermDebt",
        "CommercialPaper",
    ]


def test_total_debt_current_noncurrent_uses_latest_valid_common_context():
    facts = _companyfacts(
        LongTermDebtCurrent=_fact_series(
            _observation(12, fy=2025),
            _observation(
                10, fy=2024, filed="2024-10-31", end="2024-09-28"
            ),
        ),
        LongTermDebtNoncurrent=_fact(
            70, fy=2024, filed="2024-10-31", end="2024-09-28"
        ),
    )
    fact = total_debt_fact(facts)
    assert fact.value == 80
    assert fact.fiscal_year == 2024
    assert [part.fiscal_year for part in fact.components] == [2024, 2024]


def test_total_debt_prefers_short_term_borrowings_over_commercial_paper():
    fact = total_debt_fact(
        _companyfacts(
            LongTermDebt=90,
            ShortTermBorrowings=10,
            CommercialPaper=8,
        )
    )
    assert fact.value == 100
    assert [part.tag for part in fact.components] == [
        "LongTermDebt",
        "ShortTermBorrowings",
    ]


def test_total_debt_accepts_10k_and_10ka_in_same_reporting_period():
    facts = _companyfacts(
        LongTermDebtCurrent=_fact(12, form="10-K"),
        LongTermDebtNoncurrent=_fact(
            78, form="10-K/A", filed="2025-11-15"
        ),
    )
    fact = total_debt_fact(facts)
    assert fact.value == 90
    assert [part.form for part in fact.components] == ["10-K", "10-K/A"]
    assert [part.filed for part in fact.components] == [
        "2025-10-31",
        "2025-11-15",
    ]


def test_total_debt_without_common_reporting_context_is_unknown():
    facts = _companyfacts(
        LongTermDebt=_fact(90, fy=2025),
        ShortTermBorrowings=_fact(
            6, fy=2024, filed="2024-10-31", end="2024-09-28"
        ),
    )
    fact = total_debt_fact(facts)
    assert fact.value is None
    assert fact.reason_code == "XBRL_TOTAL_DEBT_COMPATIBLE_CONTEXT_MISSING"


def test_aapl_total_debt_exact_regression_and_snapshot_component_lineage():
    facts = _companyfacts(
        LongTermDebt=90_678_000_000,
        LongTermDebtCurrent=12_350_000_000,
        LongTermDebtNoncurrent=78_328_000_000,
        CommercialPaper=7_979_000_000,
        FinanceLeaseLiability=1_000_000_000,
    )
    snapshot = build_statement_snapshot(
        facts,
        cik_record=CikRecord(ticker="AAPL", cik="320193", exchange="US"),
        source_path="synthetic-companyfacts.json",
        valuation_date="2025-10-31",
    )

    assert snapshot["fields"]["total_debt"]["value"] == 98_657_000_000
    assert snapshot["payload_updates"]["total_debt"] == 98_657_000_000
    field = snapshot["fields"]["total_debt"]
    assert field["tag"] is None
    assert field["transform"] == "sum_declared_debt_components"
    assert [part["tag"] for part in field["components"]] == [
        "LongTermDebt",
        "CommercialPaper",
    ]
    lineage = snapshot["payload_updates"]["lineage"]["field_lineage"]["total_debt"]
    assert lineage["source_field"] is None
    assert "+" not in str(lineage["source_field"])
    assert lineage["provider"] == "sec_companyfacts"
    assert lineage["source_quality"] == "exact"
    assert lineage["source_class"] == "E0"
    assert lineage["tier"] == "official_filing"
    assert lineage["component_source_fields"] == [
        "us-gaap:LongTermDebt",
        "us-gaap:CommercialPaper",
    ]
    assert lineage["transform"] == "sum_declared_debt_components"
    assert lineage["fiscal_year"] == 2025
    assert lineage["fiscal_period"] == "FY"
    assert lineage["form"] == "10-K"
    assert lineage["as_of"] == "2025-10-31"
    assert lineage["source_path"] == "synthetic-companyfacts.json"
    assert lineage["reason_code"] == "TOTAL_DEBT_DERIVED_FROM_DECLARED_COMPONENTS"
