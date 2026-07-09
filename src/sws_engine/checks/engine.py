"""Check engine: runs the 30 Snowflake checks (+ optional management flags)
with the full result contract. Health set selection (SPEC 5.4-5.6):
financial institutions -> HF1-HF6; loss-making -> H1-H4 + cash runway;
otherwise standard H1-H6."""
from sws_engine.checks import dividend, future, health, past, value
from sws_engine.checks import health_financial, health_loss_making, management
from sws_engine.checks._helpers import CheckContext
from sws_engine.core.enums import SourceQuality

FINANCIAL_TYPES = ("bank", "insurance", "other_financial")


def run_all_checks(payload: dict, assumptions: dict, field_quality: dict,
                   fair_value):
    ctx = CheckContext(payload, assumptions, field_quality)
    checks = []
    checks += value.run(ctx, fair_value)
    checks += future.run(ctx)
    checks += past.run(ctx)

    ctype = (payload.get("company_type") or "non_financial").lower()
    if ctype in FINANCIAL_TYPES:
        checks += health_financial.run(ctx)
    elif health_loss_making.is_loss_making(ctx):
        std = health.run(ctx)
        checks += std[:4] + health_loss_making.runway_checks(ctx)
    else:
        checks += health.run(ctx)

    checks += dividend.run(ctx)
    snowflake = [c for c in checks if c.axis != "management"]
    assert len(snowflake) == 30, \
        f"check engine must emit exactly 30 Snowflake checks, got {len(snowflake)}"

    if payload.get("include_management") is True:
        checks += management.run(ctx)  # informational; excluded from scores

    missing_fields = {f for f, q in field_quality.items()
                      if q == SourceQuality.MISSING.value}
    for c in checks:
        if c.result == "UNKNOWN" and c.reason_code == "MISSING_INPUT":
            if any(f in missing_fields for f in c.inputs.keys()) or \
               any(f in missing_fields for f in _dep_fields(c)):
                c.reason_code = "PROVIDER_LIMITATION"
    return checks


def _dep_fields(check):
    deps = {
        ("value", 3): ["market_averages"],
        ("value", 4): ["industry_averages"],
        ("value", 6): ["intangible_assets"],
        ("future", 6): ["roe_3y_estimate"],
        ("dividend", 6): ["estimated_payout_3y"],
        ("health", 2): ["bank_deposits_npl_chargeoffs"],
        ("health", 5): ["bank_deposits_npl_chargeoffs"],
        ("health", 6): ["bank_deposits_npl_chargeoffs"],
    }
    return deps.get((check.axis, check.id), [])
