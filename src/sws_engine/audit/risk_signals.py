"""P0.7 business risk signals: red flags, accounting quality and capital allocation.

These are auxiliary audit outputs. They do not change the v3.1 check engine,
scoring, valuation or canonical output_schema.json. Missing data remains UNKNOWN.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

QUALITY_ORDER = {"exact": 4, "approximation": 3, "assumption": 2, "missing": 1, "unknown": 0, "UNKNOWN": 0}


def build_business_risk_package(
    input_payload: Mapping[str, Any] | None = None,
    *,
    output: Mapping[str, Any] | None = None,
    audit_summary: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> Dict[str, Any]:
    """Build a deterministic business-risk package from an input payload/output.

    P0.7 scope intentionally uses only already-available fields. It does not
    fetch external data, infer missing values or mutate the base engine result.
    """
    payload = dict(input_payload or {})
    out = dict(output or {})
    ticker = payload.get("ticker") or out.get("ticker") or (audit_summary or {}).get("ticker") or "UNKNOWN"
    valuation_date = payload.get("valuation_date") or out.get("valuation_date") or (audit_summary or {}).get("valuation_date") or "UNKNOWN"
    red_flag_checks = evaluate_red_flags(payload, output=out)
    accounting_quality = assess_accounting_quality(payload)
    capital_allocation = assess_capital_allocation(payload)
    red_flags = [flag for flag in red_flag_checks if flag.get("status") == "FAIL"]
    manual_items = manual_review_items(red_flag_checks, accounting_quality, capital_allocation)
    status = "PASS_WITH_LIMITATIONS"
    if not payload and not out:
        status = "UNKNOWN"
    elif all(flag.get("status") == "UNKNOWN" for flag in red_flag_checks) and accounting_quality.get("status") == "UNKNOWN" and capital_allocation.get("status") == "UNKNOWN":
        status = "UNKNOWN"
    return {
        "schema_version": "business_risk_package.v0.1",
        "sprint": "v4.0-p0.7",
        "status": status,
        "reason_code": "BUSINESS_RISK_SIGNALS_COMPUTED" if status != "UNKNOWN" else "BUSINESS_RISK_INPUTS_MISSING",
        "ticker": ticker,
        "valuation_date": valuation_date,
        "run_id": run_id or (audit_summary or {}).get("run_id"),
        "provider_profile": payload.get("provider_profile") or out.get("provider_profile") or (audit_summary or {}).get("provider_profile") or "UNKNOWN",
        "red_flags_summary": {
            "fail_count": len(red_flags),
            "unknown_count": sum(1 for f in red_flag_checks if f.get("status") == "UNKNOWN"),
            "pass_count": sum(1 for f in red_flag_checks if f.get("status") == "PASS"),
            "high_severity_fail_count": sum(1 for f in red_flags if f.get("severity") == "HIGH"),
        },
        "red_flags": red_flags,
        "red_flag_checks": red_flag_checks,
        "accounting_quality": accounting_quality,
        "capital_allocation": capital_allocation,
        "manual_review_items": manual_items,
        "source_quality": aggregate_source_quality(red_flag_checks + accounting_quality.get("metrics", []) + capital_allocation.get("metrics", [])),
        "source_class": aggregate_source_class(red_flag_checks + accounting_quality.get("metrics", []) + capital_allocation.get("metrics", [])),
        "input_lineage_summary": input_lineage_summary(payload),
        "not_investment_advice": True,
        "limitations": [
            "P0.7 uses only supplied payload/output fields; no external data is fetched.",
            "These signals are auxiliary audit artifacts and are not v3.1 Snowflake checks.",
            "Missing fields remain UNKNOWN and are surfaced as manual review items.",
        ],
    }


def evaluate_red_flags(payload: Mapping[str, Any], *, output: Mapping[str, Any] | None = None) -> List[Dict[str, Any]]:
    fcf = adjusted_fcf(payload)
    ocf = num(payload.get("operating_cash_flow"))
    ni = num(first_present(payload, ["net_income", "latest_net_income", "earnings", "ttm_net_income"]))
    total_assets = num(payload.get("total_assets"))
    intangibles = num(payload.get("intangible_assets"))
    total_debt = num(payload.get("total_debt"))
    cash = num(first_present(payload, ["cash_and_st_investments", "cash", "cash_and_equivalents"]))
    equity = num(payload.get("equity"))
    dividends_paid = abs_or_none(first_present(payload, ["dividends_paid", "dividends", "cash_dividends_paid"]))
    shares_hist = nums(first_present(payload, ["shares_outstanding_history", "share_count_history", "shares_history"]))

    checks = [
        _signal(
            payload,
            "NEGATIVE_OPERATING_CASH_FLOW",
            ["operating_cash_flow"],
            ocf is not None and ocf < 0,
            ocf is None,
            "HIGH",
            "RED_FLAG_NEGATIVE_OPERATING_CASH_FLOW",
            {"operating_cash_flow": ocf},
        ),
        _signal(
            payload,
            "NEGATIVE_FREE_CASH_FLOW",
            ["operating_cash_flow", "capex_history_3y"],
            fcf is not None and fcf < 0,
            fcf is None,
            "HIGH",
            "RED_FLAG_NEGATIVE_FREE_CASH_FLOW",
            {"adjusted_fcf": fcf, "operating_cash_flow": ocf, "capex_history_3y": first_present(payload, ["capex_history_3y", "capex_history"])},
        ),
        _signal(
            payload,
            "EARNINGS_CASH_FLOW_DIVERGENCE",
            ["net_income", "operating_cash_flow", "capex_history_3y"],
            ni is not None and ni > 0 and (ocf is not None and ocf < 0 or fcf is not None and fcf < 0),
            ni is None or ocf is None or fcf is None,
            "HIGH",
            "RED_FLAG_EARNINGS_CASH_FLOW_DIVERGENCE",
            {"net_income": ni, "operating_cash_flow": ocf, "adjusted_fcf": fcf},
        ),
        _signal(
            payload,
            "DIVIDEND_NOT_COVERED_BY_FCF",
            ["dividends_paid", "operating_cash_flow", "capex_history_3y"],
            dividends_paid is not None and dividends_paid > 0 and (fcf is not None and dividends_paid > max(fcf, 0)),
            dividends_paid is None or fcf is None,
            "HIGH",
            "RED_FLAG_DIVIDEND_NOT_COVERED_BY_FCF",
            {"dividends_paid_abs": dividends_paid, "adjusted_fcf": fcf},
        ),
        _signal(
            payload,
            "HIGH_INTANGIBLES_TO_ASSETS",
            ["intangible_assets", "total_assets"],
            intangibles is not None and total_assets not in (None, 0) and intangibles / total_assets > 0.50,
            intangibles is None or total_assets in (None, 0),
            "MEDIUM",
            "RED_FLAG_HIGH_INTANGIBLES_TO_ASSETS",
            {"intangible_assets": intangibles, "total_assets": total_assets, "intangibles_to_assets": safe_div(intangibles, total_assets)},
        ),
        _signal(
            payload,
            "ELEVATED_NET_DEBT_TO_EQUITY",
            ["total_debt", "cash_and_st_investments", "equity"],
            total_debt is not None and cash is not None and equity not in (None, 0) and (total_debt - cash) / equity > 1.5,
            total_debt is None or cash is None or equity in (None, 0),
            "MEDIUM",
            "RED_FLAG_ELEVATED_NET_DEBT_TO_EQUITY",
            {"total_debt": total_debt, "cash": cash, "equity": equity, "net_debt_to_equity": safe_div(None if total_debt is None or cash is None else total_debt - cash, equity)},
        ),
        _signal(
            payload,
            "SHARE_DILUTION_ABOVE_10PCT",
            ["shares_outstanding_history"],
            len(shares_hist) >= 2 and shares_hist[0] not in (0, None) and (shares_hist[-1] / shares_hist[0] - 1.0) > 0.10,
            len(shares_hist) < 2 or shares_hist[0] in (0, None),
            "MEDIUM",
            "RED_FLAG_SHARE_DILUTION_ABOVE_10PCT",
            {"shares_start": shares_hist[0] if shares_hist else None, "shares_end": shares_hist[-1] if shares_hist else None, "share_count_growth_pct": share_growth(shares_hist)},
        ),
    ]
    # Escalate if base engine already reported many unknowns.
    unknown_checks = sum(1 for ch in (output or {}).get("checks", []) if ch.get("result") == "UNKNOWN")
    if unknown_checks:
        checks.append({
            "flag_id": "ENGINE_UNKNOWN_CHECKS_PRESENT",
            "status": "FAIL" if unknown_checks >= 5 else "PASS",
            "severity": "MEDIUM" if unknown_checks >= 5 else "INFO",
            "reason_code": "RED_FLAG_ENGINE_UNKNOWN_CHECKS_PRESENT",
            "evidence": {"unknown_checks_count": unknown_checks},
            "source_quality": "exact",
            "source_class": "E0",
            "input_lineage": {"source": "engine_output.checks"},
        })
    return checks


def assess_accounting_quality(payload: Mapping[str, Any]) -> Dict[str, Any]:
    metrics: list[dict[str, Any]] = []
    ocf = num(payload.get("operating_cash_flow"))
    ni = num(first_present(payload, ["net_income", "latest_net_income", "earnings", "ttm_net_income"]))
    assets = num(payload.get("total_assets"))
    fcf = adjusted_fcf(payload)

    metrics.append(_metric(payload, "ACCRUALS_RATIO", ["net_income", "operating_cash_flow", "total_assets"], safe_div(None if ni is None or ocf is None else ni - ocf, assets), warn_abs_gt=0.10, fail_abs_gt=0.20, reason_code="ACCOUNTING_QUALITY_ACCRUALS_RATIO"))
    metrics.append(_metric(payload, "FCF_CONVERSION", ["operating_cash_flow", "capex_history_3y", "net_income"], safe_div(fcf, ni), warn_lt=0.80, fail_lt=0.60, reason_code="ACCOUNTING_QUALITY_FCF_CONVERSION"))

    revenue_hist = nums(first_present(payload, ["revenue_history", "revenues_history"]))
    gross_hist = nums(first_present(payload, ["gross_profit_history", "gross_margin_history"]))
    if len(revenue_hist) >= 2 and len(gross_hist) == len(revenue_hist):
        margins = [safe_div(g, r) for g, r in zip(gross_hist, revenue_hist) if r not in (None, 0)]
        val = (max(margins) - min(margins)) if len(margins) >= 2 else None
        metrics.append(_metric(payload, "GROSS_MARGIN_VARIABILITY", ["gross_profit_history", "revenue_history"], val, warn_gt=0.10, fail_gt=0.20, reason_code="ACCOUNTING_QUALITY_MARGIN_VARIABILITY"))
    else:
        metrics.append(_unknown_metric(payload, "GROSS_MARGIN_VARIABILITY", ["gross_profit_history", "revenue_history"], "BUSINESS_RISK_INPUTS_MISSING"))

    evaluated = [m for m in metrics if m["status"] != "UNKNOWN"]
    weak = [m for m in evaluated if m["status"] == "FAIL"]
    watch = [m for m in evaluated if m["status"] == "WATCH"]
    if len(evaluated) < 2:
        grade, status, reason = "UNKNOWN", "UNKNOWN", "BUSINESS_RISK_INPUTS_MISSING"
    elif weak:
        grade, status, reason = "WEAK", "PASS_WITH_LIMITATIONS", "ACCOUNTING_QUALITY_WEAK"
    elif watch:
        grade, status, reason = "WATCH", "PASS_WITH_LIMITATIONS", "ACCOUNTING_QUALITY_WATCH"
    else:
        grade = "STRONG" if all(m.get("status") == "PASS" for m in evaluated) and len(evaluated) >= 2 else "NORMAL"
        status, reason = "PASS", "ACCOUNTING_QUALITY_NORMAL"
    return {
        "status": status,
        "grade": grade,
        "reason_code": reason,
        "metrics": metrics,
        "source_quality": aggregate_source_quality(metrics),
        "source_class": aggregate_source_class(metrics),
        "input_lineage_summary": lineage_for_fields(payload, sorted({f for m in metrics for f in m.get("fields", [])})),
    }


def assess_capital_allocation(payload: Mapping[str, Any]) -> Dict[str, Any]:
    fcf = adjusted_fcf(payload)
    dividends = abs_or_none(first_present(payload, ["dividends_paid", "dividends", "cash_dividends_paid"]))
    buybacks = abs_or_none(first_present(payload, ["buybacks", "share_repurchases", "repurchase_of_stock", "repurchases_of_common_stock"]))
    revenue = num(first_present(payload, ["revenue", "latest_revenue", "ttm_revenue"]))
    capex_avg = average_abs(nums(first_present(payload, ["capex_history_3y", "capex_history"])))
    shares_hist = nums(first_present(payload, ["shares_outstanding_history", "share_count_history", "shares_history"]))

    metrics = [
        _metric(payload, "DIVIDENDS_TO_FCF", ["dividends_paid", "operating_cash_flow", "capex_history_3y"], safe_div(dividends, fcf), warn_gt=0.80, fail_gt=1.00, reason_code="CAPITAL_ALLOCATION_DIVIDENDS_TO_FCF"),
        _metric(payload, "BUYBACKS_TO_FCF", ["buybacks", "operating_cash_flow", "capex_history_3y"], safe_div(buybacks, fcf), warn_gt=0.80, fail_gt=1.00, reason_code="CAPITAL_ALLOCATION_BUYBACKS_TO_FCF"),
        _metric(payload, "CAPEX_INTENSITY", ["capex_history_3y", "revenue"], safe_div(capex_avg, revenue), warn_gt=0.25, fail_gt=0.40, reason_code="CAPITAL_ALLOCATION_CAPEX_INTENSITY"),
        _metric(payload, "SHARE_COUNT_GROWTH", ["shares_outstanding_history"], share_growth(shares_hist), warn_gt=0.05, fail_gt=0.10, reason_code="CAPITAL_ALLOCATION_SHARE_COUNT_GROWTH"),
    ]
    evaluated = [m for m in metrics if m["status"] != "UNKNOWN"]
    weak = [m for m in evaluated if m["status"] == "FAIL"]
    watch = [m for m in evaluated if m["status"] == "WATCH"]
    if not evaluated:
        status, assessment, reason = "UNKNOWN", "UNKNOWN", "BUSINESS_RISK_INPUTS_MISSING"
    elif weak:
        status, assessment, reason = "PASS_WITH_LIMITATIONS", "WATCH", "CAPITAL_ALLOCATION_WATCH"
    elif watch:
        status, assessment, reason = "PASS_WITH_LIMITATIONS", "WATCH", "CAPITAL_ALLOCATION_WATCH"
    else:
        status, assessment, reason = "PASS", "BALANCED", "CAPITAL_ALLOCATION_BALANCED"
    return {
        "status": status,
        "assessment": assessment,
        "reason_code": reason,
        "metrics": metrics,
        "source_quality": aggregate_source_quality(metrics),
        "source_class": aggregate_source_class(metrics),
        "input_lineage_summary": lineage_for_fields(payload, sorted({f for m in metrics for f in m.get("fields", [])})),
    }


def write_business_risk_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> Dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(package.get("ticker") or "UNKNOWN")
    json_path = out / f"{ticker}_business_risk_package.json"
    md_path = out / f"{ticker}_business_risk_report.md"
    json_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(business_risk_report_md(package), encoding="utf-8")
    return {"business_risk_package_json": str(json_path), "business_risk_report_md": str(md_path)}


def business_risk_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        f"# Business Risk Signals — {package.get('ticker', 'UNKNOWN')}",
        "",
        "## Audit scope",
        "",
        "This is an auxiliary audit report. It is not a Snowflake score and not investment advice.",
        "",
        f"- Status: `{package.get('status')}`",
        f"- Reason code: `{package.get('reason_code')}`",
        f"- Run ID: `{package.get('run_id') or 'UNKNOWN'}`",
        f"- Provider profile: `{package.get('provider_profile')}`",
        "",
        "## Red flags",
        "",
    ]
    flags = package.get("red_flags") or []
    if not flags:
        lines.append("No triggered red flags were detected from the supplied fields. UNKNOWN checks may still require manual review.")
    else:
        for flag in flags:
            lines.append(f"- **{flag.get('severity')}** `{flag.get('flag_id')}` — `{flag.get('reason_code')}`; evidence={json.dumps(flag.get('evidence'), sort_keys=True)}")
    lines += ["", "## Accounting quality", ""]
    aq = package.get("accounting_quality") or {}
    lines.append(f"- Grade: **{aq.get('grade', 'UNKNOWN')}** (`{aq.get('reason_code', 'UNKNOWN')}`)")
    for metric in aq.get("metrics") or []:
        lines.append(f"  - `{metric.get('metric_id')}`: {metric.get('status')} value={metric.get('value')} reason={metric.get('reason_code')}")
    lines += ["", "## Capital allocation", ""]
    ca = package.get("capital_allocation") or {}
    lines.append(f"- Assessment: **{ca.get('assessment', 'UNKNOWN')}** (`{ca.get('reason_code', 'UNKNOWN')}`)")
    for metric in ca.get("metrics") or []:
        lines.append(f"  - `{metric.get('metric_id')}`: {metric.get('status')} value={metric.get('value')} reason={metric.get('reason_code')}")
    lines += ["", "## Manual review items", ""]
    for item in package.get("manual_review_items") or []:
        lines.append(f"- `{item.get('reason_code')}` — {item.get('message')}")
    if not package.get("manual_review_items"):
        lines.append("No manual review items were generated by P0.7.")
    return "\n".join(lines) + FOOTER


def business_risk_company_to_files(
    output_dir: str | Path,
    *,
    input_path: str | None = None,
    db_path: str | None = None,
    ticker: str | None = None,
    run_id: str | None = None,
) -> Dict[str, Any]:
    if input_path:
        payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
        package = build_business_risk_package(payload)
    else:
        if not db_path or not ticker:
            raise ValueError("Either --input or both --ticker/--db are required")
        from sws_engine.audit.audit_summary import build_audit_summary, load_latest_audit_context_from_db
        ctx = load_latest_audit_context_from_db(db_path, ticker, run_id=run_id)
        audit = build_audit_summary(
            ctx["output"],
            run_id=ctx["run_id"],
            input_payload=ctx.get("input_payload"),
            assumptions_hash=ctx.get("assumptions_hash"),
            engine_version=ctx.get("engine_version"),
        )
        package = build_business_risk_package(ctx.get("input_payload"), output=ctx["output"], audit_summary=audit, run_id=ctx["run_id"])
    paths = write_business_risk_artifacts(package, output_dir)
    return {"package": package, "paths": paths}


def _signal(payload: Mapping[str, Any], flag_id: str, fields: Sequence[str], condition: bool, unknown: bool, severity: str, reason_code: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    status = "UNKNOWN" if unknown else ("FAIL" if condition else "PASS")
    rc = "BUSINESS_RISK_INPUTS_MISSING" if unknown else reason_code
    return {
        "flag_id": flag_id,
        "status": status,
        "severity": severity if status == "FAIL" else ("INFO" if status == "PASS" else "WARN"),
        "reason_code": rc,
        "fields": list(fields),
        "evidence": evidence,
        "source_quality": quality_for_fields(payload, fields, unknown=unknown),
        "source_class": source_class_for_fields(payload, fields),
        "input_lineage": lineage_for_fields(payload, fields),
    }


def _metric(payload: Mapping[str, Any], metric_id: str, fields: Sequence[str], value: float | None, *, reason_code: str, warn_gt: float | None = None, fail_gt: float | None = None, warn_abs_gt: float | None = None, fail_abs_gt: float | None = None, warn_lt: float | None = None, fail_lt: float | None = None) -> Dict[str, Any]:
    if value is None:
        return _unknown_metric(payload, metric_id, fields, "BUSINESS_RISK_INPUTS_MISSING")
    status = "PASS"
    if fail_gt is not None and value > fail_gt or fail_abs_gt is not None and abs(value) > fail_abs_gt or fail_lt is not None and value < fail_lt:
        status = "FAIL"
    elif warn_gt is not None and value > warn_gt or warn_abs_gt is not None and abs(value) > warn_abs_gt or warn_lt is not None and value < warn_lt:
        status = "WATCH"
    return {
        "metric_id": metric_id,
        "status": status,
        "reason_code": reason_code,
        "value": value,
        "fields": list(fields),
        "source_quality": quality_for_fields(payload, fields, unknown=False),
        "source_class": source_class_for_fields(payload, fields),
        "input_lineage": lineage_for_fields(payload, fields),
    }


def _unknown_metric(payload: Mapping[str, Any], metric_id: str, fields: Sequence[str], reason_code: str) -> Dict[str, Any]:
    return {
        "metric_id": metric_id,
        "status": "UNKNOWN",
        "reason_code": reason_code,
        "value": None,
        "fields": list(fields),
        "source_quality": "missing",
        "source_class": source_class_for_fields(payload, fields),
        "input_lineage": lineage_for_fields(payload, fields),
    }


def manual_review_items(red_flags: Sequence[Mapping[str, Any]], accounting_quality: Mapping[str, Any], capital_allocation: Mapping[str, Any]) -> List[Dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for flag in red_flags:
        if flag.get("status") == "FAIL":
            items.append({"reason_code": flag.get("reason_code"), "message": f"Review triggered red flag {flag.get('flag_id')} before relying on the analysis."})
        elif flag.get("status") == "UNKNOWN":
            items.append({"reason_code": "BUSINESS_RISK_INPUTS_MISSING", "message": f"Populate or accept UNKNOWN for red-flag input fields: {', '.join(flag.get('fields') or [])}."})
    for component_name, component in (("accounting_quality", accounting_quality), ("capital_allocation", capital_allocation)):
        if component.get("status") == "UNKNOWN":
            items.append({"reason_code": "BUSINESS_RISK_INPUTS_MISSING", "message": f"{component_name} could not be assessed because inputs are missing."})
        elif component.get("status") == "PASS_WITH_LIMITATIONS":
            items.append({"reason_code": component.get("reason_code"), "message": f"{component_name} requires manual review: {component.get('reason_code')}."})
    # deterministic de-dupe
    seen = set()
    out = []
    for item in items:
        key = (item.get("reason_code"), item.get("message"))
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def first_present(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in payload and payload.get(key) is not None:
            return payload.get(key)
    return None


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def nums(value: Any) -> List[float]:
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    for item in value:
        n = num(item)
        if n is not None:
            out.append(n)
    return out


def abs_or_none(value: Any) -> float | None:
    n = num(value)
    return abs(n) if n is not None else None


def average_abs(values: Sequence[float]) -> float | None:
    return sum(abs(v) for v in values) / len(values) if values else None


def adjusted_fcf(payload: Mapping[str, Any]) -> float | None:
    ocf = num(payload.get("operating_cash_flow"))
    capex = nums(first_present(payload, ["capex_history_3y", "capex_history"]))
    if ocf is None or not capex:
        return None
    return ocf - average_abs(capex)


def safe_div(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom in (None, 0):
        return None
    return numer / denom


def share_growth(shares: Sequence[float]) -> float | None:
    if len(shares) < 2 or shares[0] == 0:
        return None
    return shares[-1] / shares[0] - 1.0


def lineage_for_fields(payload: Mapping[str, Any], fields: Iterable[str]) -> Dict[str, Any]:
    lineage = ((payload.get("lineage") or {}).get("field_lineage") or {}) if isinstance(payload.get("lineage"), Mapping) else {}
    out: dict[str, Any] = {}
    for field in fields:
        meta = lineage.get(field) or {}
        out[field] = meta if meta else {"source_quality": "unknown", "source_class": "UNKNOWN", "reason_code": "LINEAGE_NOT_PROVIDED"}
    return out


def input_lineage_summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    lineage = ((payload.get("lineage") or {}).get("field_lineage") or {}) if isinstance(payload.get("lineage"), Mapping) else {}
    return {"field_lineage_count": len(lineage), "fields": sorted(lineage.keys())}


def quality_for_fields(payload: Mapping[str, Any], fields: Iterable[str], *, unknown: bool) -> str:
    if unknown:
        return "missing"
    qualities = []
    for meta in lineage_for_fields(payload, fields).values():
        qualities.append(str(meta.get("source_quality") or "unknown"))
    if not qualities:
        return "unknown"
    # Conservative: take the lowest quality among required fields.
    return min(qualities, key=lambda q: QUALITY_ORDER.get(q, 0))


def source_class_for_fields(payload: Mapping[str, Any], fields: Iterable[str]) -> str:
    classes = []
    for meta in lineage_for_fields(payload, fields).values():
        cls = str(meta.get("source_class") or "UNKNOWN")
        if cls != "UNKNOWN":
            classes.append(cls)
    return sorted(classes)[0] if classes else "UNKNOWN"


def aggregate_source_quality(items: Sequence[Mapping[str, Any]]) -> str:
    qualities = [str(item.get("source_quality") or "unknown") for item in items]
    return min(qualities, key=lambda q: QUALITY_ORDER.get(q, 0)) if qualities else "unknown"


def aggregate_source_class(items: Sequence[Mapping[str, Any]]) -> str:
    classes = [str(item.get("source_class") or "UNKNOWN") for item in items if item.get("source_class")]
    known = [cls for cls in classes if cls != "UNKNOWN"]
    return sorted(known)[0] if known else "UNKNOWN"
