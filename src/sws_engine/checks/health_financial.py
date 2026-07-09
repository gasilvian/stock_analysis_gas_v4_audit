"""HEALTH checks HF1-HF6 for financial institutions (SPEC 5.6)."""
from sws_engine.checks._helpers import CheckContext, binary_check
from sws_engine.core.enums import Axis, ReasonCode
from sws_engine.core.result import unknown_check

FIN = ("financials_as_of",)


def run(ctx: CheckContext):
    checks = []
    bank = ctx.payload.get("bank_deposits_npl_chargeoffs") or {}

    def b(k):
        v = bank.get(k)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    total_assets = ctx.num("total_assets")
    equity = ctx.num("equity")
    total_liabilities = ctx.num("total_liabilities")
    deposits, npl, allowance = b("deposits"), b("npl"), b("allowance_npl")
    net_loans, charge_offs = b("net_loans"), b("net_charge_offs")

    thr = "Total Assets < 20 * Equity"
    if equity is None or equity <= 0 or total_assets is None:
        rc = ReasonCode.MISSING_INPUT if equity is None or total_assets is None \
            else ReasonCode.NEGATIVE_DENOMINATOR
        checks.append(unknown_check(Axis.HEALTH, 1, "hf_assets_to_equity_below_20x",
                                    rc, {"total_assets": total_assets,
                                         "equity": equity}, thr, ctx.lineage(*FIN)))
    else:
        checks.append(binary_check(
            ctx, axis=Axis.HEALTH, id=1, name="hf_assets_to_equity_below_20x",
            condition_inputs={"total_assets": total_assets, "equity": equity},
            lineage_fields=FIN, threshold=thr,
            passes=total_assets < 20 * equity,
            quality_fields=("total_assets", "equity")))

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=2, name="hf_allowance_covers_npl",
        condition_inputs={"allowance_npl": allowance, "npl": npl},
        lineage_fields=FIN, threshold="Allowance NPL > 100% * NPL",
        passes=allowance is not None and npl is not None and allowance > npl,
        quality_fields=("bank_deposits_npl_chargeoffs",)))

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=3, name="hf_deposits_primary_funding",
        condition_inputs={"deposits": deposits,
                          "total_liabilities": total_liabilities},
        lineage_fields=FIN, threshold="Deposits > 50% * Total Liabilities",
        passes=deposits is not None and total_liabilities is not None
        and deposits > 0.5 * total_liabilities,
        quality_fields=("bank_deposits_npl_chargeoffs", "total_liabilities")))

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=4, name="hf_loans_to_assets_below_110pct",
        condition_inputs={"net_loans": net_loans, "total_assets": total_assets},
        lineage_fields=FIN, threshold="Net Loans < 110% * Total Assets",
        passes=net_loans is not None and total_assets is not None
        and net_loans < 1.10 * total_assets,
        quality_fields=("bank_deposits_npl_chargeoffs", "total_assets")))

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=5, name="hf_loans_to_deposits_below_125pct",
        condition_inputs={"net_loans": net_loans, "deposits": deposits},
        lineage_fields=FIN, threshold="Loans < 125% * Deposits",
        passes=net_loans is not None and deposits is not None
        and net_loans < 1.25 * deposits,
        quality_fields=("bank_deposits_npl_chargeoffs",)))

    checks.append(binary_check(
        ctx, axis=Axis.HEALTH, id=6, name="hf_charge_offs_below_3pct_loans",
        condition_inputs={"net_charge_offs": charge_offs, "net_loans": net_loans},
        lineage_fields=FIN, threshold="Net Charge-Offs < 3% * Loans",
        passes=charge_offs is not None and net_loans is not None
        and charge_offs < 0.03 * net_loans,
        quality_fields=("bank_deposits_npl_chargeoffs",)))
    return checks
