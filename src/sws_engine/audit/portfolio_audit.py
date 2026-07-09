"""P0.10 Portfolio Audit Minimal foundation.

This module audits a local holdings CSV using already-produced audit, thesis,
sensitivity and optional business-risk artifacts. It does not fetch live data,
does not calculate allocation advice and does not change the canonical v3.1
portfolio engine or output_schema.json. Missing artifacts remain UNKNOWN and
are surfaced as portfolio-level exposure.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

FOOTER = (
    "\n---\n"
    "Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St "
    "(Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. "
    "Acest raport este pentru uz intern/personal/educațional. Not investment advice.\n"
)

CONFIDENCE_SCORE = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.25, "UNKNOWN": 0.0, "A": 1.0, "B": 0.8, "C": 0.6, "D": 0.25, "E": 0.0}
RISK_SCORE = {"LOW": 0.0, "MEDIUM": 0.5, "HIGH": 1.0, "UNKNOWN": 1.0}
QUALITY_RANK = {"HIGH": 5, "MEDIUM_HIGH": 4, "MEDIUM": 3, "MEDIUM_LOW": 2, "LOW": 1, "UNKNOWN": 0, "exact": 5, "approximation": 3, "assumption": 2, "missing": 0}


def load_holdings_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load a local holdings CSV.

    Required: ticker. Optional: weight, sector, factor, thesis_id, macro_exposure,
    cost_basis, current_value. Weight can be expressed as 0.25 or 25.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Holdings CSV not found: {p}")
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    holdings: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        ticker = str(row.get("ticker") or row.get("Ticker") or "").strip().upper()
        weight = _parse_weight(row.get("weight") or row.get("Weight"))
        current_value = _num(row.get("current_value") or row.get("market_value") or row.get("value"))
        if ticker == "CASH":
            weight = 0.0 if weight is None else weight
        holding = {
            "row_number": idx,
            "ticker": ticker or "UNKNOWN",
            "weight": weight,
            "current_value": current_value,
            "sector": _clean(row.get("sector") or row.get("Sector") or "UNKNOWN"),
            "factor": _clean(row.get("factor") or row.get("style") or row.get("Factor") or "UNKNOWN"),
            "thesis_id": _clean(row.get("thesis_id") or row.get("thesis") or row.get("theme") or "UNKNOWN"),
            "macro_exposure": _split_tokens(row.get("macro_exposure") or row.get("macro") or ""),
            "cost_basis": _num(row.get("cost_basis") or row.get("CostBasis")),
            "notes": _clean(row.get("notes") or row.get("comment") or ""),
            "metadata": {k: v for k, v in row.items() if k},
        }
        holdings.append(holding)
    return _normalize_missing_weights(holdings)


def build_portfolio_audit(
    holdings: Sequence[Mapping[str, Any]],
    *,
    audit_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    business_risks: Mapping[str, Mapping[str, Any]] | None = None,
    thesis_statuses: Mapping[str, Mapping[str, Any]] | None = None,
    sensitivity_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    portfolio_id: str | None = None,
    valuation_date: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic minimal portfolio audit package."""
    rows = [dict(h) for h in holdings]
    audits = {str(k).upper(): dict(v) for k, v in (audit_summaries or {}).items()}
    risks = {str(k).upper(): dict(v) for k, v in (business_risks or {}).items()}
    theses = {str(k).upper(): dict(v) for k, v in (thesis_statuses or {}).items()}
    sens = {str(k).upper(): dict(v) for k, v in (sensitivity_summaries or {}).items()}

    holdings_out = [_audit_holding(h, audits.get(str(h.get("ticker", "UNKNOWN")).upper()), risks.get(str(h.get("ticker", "UNKNOWN")).upper()), theses.get(str(h.get("ticker", "UNKNOWN")).upper()), sens.get(str(h.get("ticker", "UNKNOWN")).upper())) for h in rows]
    invested = [h for h in holdings_out if h.get("ticker") != "CASH"]
    total_weight = sum(_weight(h) for h in holdings_out)
    cash_weight = sum(_weight(h) for h in holdings_out if h.get("ticker") == "CASH")
    unknown_artifact_weight = sum(_weight(h) for h in invested if h.get("artifact_status") == "UNKNOWN")
    degraded_provider_weight = sum(_weight(h) for h in invested if h.get("provider_degradation_visible"))
    data_conf_score = _weighted_average([(h.get("data_confidence_score"), _weight(h)) for h in invested])
    conclusion_risk_score = _weighted_average([(h.get("conclusion_risk_score"), _weight(h)) for h in invested])

    sector = _concentration(holdings_out, "sector")
    factor = _concentration(holdings_out, "factor")
    thesis = _concentration(holdings_out, "thesis_id", ignore={"UNKNOWN", "", None})
    macro = _macro_sensitivity_map(holdings_out)
    attribution = _attribution_lite(holdings_out)
    manual_items = _portfolio_manual_review_items(holdings_out, sector, factor, thesis, macro, unknown_artifact_weight, degraded_provider_weight, data_conf_score, conclusion_risk_score)

    if not rows:
        status, reason = "UNKNOWN", "PORTFOLIO_INPUTS_MISSING"
    elif invested and all(h.get("artifact_status") == "UNKNOWN" for h in invested):
        status, reason = "UNKNOWN", "PORTFOLIO_AUDIT_ARTIFACTS_MISSING"
    else:
        status, reason = "PASS_WITH_LIMITATIONS", "PORTFOLIO_AUDIT_COMPUTED"

    package = {
        "schema_version": "portfolio_audit.v0.1",
        "sprint": "v4.0-p0.10",
        "status": status,
        "reason_code": reason,
        "portfolio_id": portfolio_id or "local_portfolio",
        "valuation_date": valuation_date or _first_non_empty([h.get("valuation_date") for h in holdings_out]) or "UNKNOWN",
        "holdings_count": len(rows),
        "invested_holdings_count": len(invested),
        "total_weight_pct": round(total_weight * 100, 4),
        "cash_weight_pct": round(cash_weight * 100, 4),
        "weighted_data_confidence": {
            "score": _round(data_conf_score),
            "level": _confidence_level(data_conf_score),
            "reason_code": "PORTFOLIO_WEIGHTED_DATA_CONFIDENCE_COMPUTED" if data_conf_score is not None else "PORTFOLIO_COMPONENT_UNKNOWN",
        },
        "weighted_conclusion_risk": {
            "score": _round(conclusion_risk_score),
            "level": _risk_level(conclusion_risk_score),
            "reason_code": "PORTFOLIO_WEIGHTED_CONCLUSION_RISK_COMPUTED" if conclusion_risk_score is not None else "PORTFOLIO_COMPONENT_UNKNOWN",
        },
        "unknown_exposure": {
            "weight_pct": _pct(unknown_artifact_weight),
            "count": sum(1 for h in invested if h.get("artifact_status") == "UNKNOWN"),
            "reason_code": "PORTFOLIO_UNKNOWN_EXPOSURE_PRESENT" if unknown_artifact_weight > 0 else "PORTFOLIO_NO_UNKNOWN_EXPOSURE",
        },
        "provider_degradation_exposure": {
            "weight_pct": _pct(degraded_provider_weight),
            "count": sum(1 for h in invested if h.get("provider_degradation_visible")),
            "reason_code": "PORTFOLIO_PROVIDER_DEGRADATION_EXPOSURE" if degraded_provider_weight > 0 else "PORTFOLIO_NO_PROVIDER_DEGRADATION_EXPOSURE",
        },
        "sector_concentration": sector,
        "factor_concentration": factor,
        "macro_sensitivity_map": macro,
        "single_thesis_concentration": thesis,
        "attribution_lite": attribution,
        "holdings": holdings_out,
        "manual_review_items": manual_items,
        "source_quality": _aggregate_source_quality(holdings_out),
        "source_class": _aggregate_source_class(holdings_out),
        "input_lineage": {
            "holdings": "operator_curated_local_csv_or_api_payload",
            "audit_summaries_present": bool(audits),
            "business_risks_present": bool(risks),
            "thesis_statuses_present": bool(theses),
            "sensitivity_summaries_present": bool(sens),
        },
        "limitations": [
            "P0.10 audits a local portfolio using existing audit artifacts only; it does not fetch live data.",
            "Portfolio buckets and exposures are research-process diagnostics, not allocation advice.",
            "Missing per-holding artifacts remain UNKNOWN and increase unknown exposure.",
            "Factor and macro maps are simple operator-supplied labels; missing labels remain UNKNOWN.",
        ],
        "not_investment_advice": True,
    }
    return package


def portfolio_audit_from_files(
    holdings_csv: str | Path,
    *,
    audit_dir: str | Path | None = None,
    business_risk_dir: str | Path | None = None,
    thesis_dir: str | Path | None = None,
    sensitivity_dir: str | Path | None = None,
    portfolio_id: str | None = None,
    valuation_date: str | None = None,
) -> dict[str, Any]:
    return build_portfolio_audit(
        load_holdings_csv(holdings_csv),
        audit_summaries=load_artifact_map(audit_dir, kind="audit"),
        business_risks=load_artifact_map(business_risk_dir, kind="business_risk"),
        thesis_statuses=load_artifact_map(thesis_dir, kind="thesis"),
        sensitivity_summaries=load_artifact_map(sensitivity_dir, kind="sensitivity"),
        portfolio_id=portfolio_id,
        valuation_date=valuation_date,
    )


def portfolio_audit_to_files(
    holdings_csv: str | Path,
    output_dir: str | Path,
    *,
    audit_dir: str | Path | None = None,
    business_risk_dir: str | Path | None = None,
    thesis_dir: str | Path | None = None,
    sensitivity_dir: str | Path | None = None,
    portfolio_id: str | None = None,
    valuation_date: str | None = None,
) -> dict[str, Any]:
    package = portfolio_audit_from_files(
        holdings_csv,
        audit_dir=audit_dir,
        business_risk_dir=business_risk_dir,
        thesis_dir=thesis_dir,
        sensitivity_dir=sensitivity_dir,
        portfolio_id=portfolio_id,
        valuation_date=valuation_date,
    )
    return {"package": package, "paths": write_portfolio_audit_artifacts(package, output_dir)}


def load_artifact_map(path: str | Path | None, *, kind: str) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    base = Path(path)
    if not base.exists():
        raise FileNotFoundError(f"Artifact directory not found: {base}")
    artifacts: dict[str, dict[str, Any]] = {}
    for pattern in ("*.json", "*/*.json"):
        for p in base.glob(pattern):
            if p.is_dir():
                continue
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not _looks_like(obj, kind):
                continue
            ticker = str(obj.get("ticker") or "").upper()
            if ticker:
                artifacts[ticker] = obj
    return artifacts


def render_portfolio_audit_report_md(package: Mapping[str, Any]) -> str:
    lines = [
        "# Portfolio Audit Report",
        "",
        "## Verdict",
        "",
        f"- Status: `{package.get('status', 'UNKNOWN')}`",
        f"- Reason code: `{package.get('reason_code', 'UNKNOWN')}`",
        f"- Portfolio ID: `{package.get('portfolio_id', 'UNKNOWN')}`",
        f"- Holdings count: `{package.get('holdings_count', 0)}`",
        f"- Weighted data confidence: `{(package.get('weighted_data_confidence') or {}).get('level', 'UNKNOWN')}`",
        f"- Weighted conclusion risk: `{(package.get('weighted_conclusion_risk') or {}).get('level', 'UNKNOWN')}`",
        f"- Unknown exposure: `{(package.get('unknown_exposure') or {}).get('weight_pct', 0)}%`",
        "",
        "## Concentration",
        "",
        "| Dimension | Top bucket | Top weight % | HHI | Reason code |",
        "|---|---|---:|---:|---|",
    ]
    for key, label in (("sector_concentration", "Sector"), ("factor_concentration", "Factor"), ("single_thesis_concentration", "Thesis")):
        obj = package.get(key) or {}
        lines.append(f"| {label} | `{obj.get('top_bucket', 'UNKNOWN')}` | {obj.get('top_weight_pct', 0)} | {obj.get('hhi', 0)} | `{obj.get('reason_code', 'UNKNOWN')}` |")
    lines += [
        "",
        "## Macro sensitivity map",
        "",
        "| Macro exposure | Weight % | Holdings |",
        "|---|---:|---|",
    ]
    exposures = (package.get("macro_sensitivity_map") or {}).get("exposures") or []
    if exposures:
        for row in exposures:
            lines.append(f"| `{row.get('exposure')}` | {row.get('weight_pct')} | {', '.join(row.get('tickers') or [])} |")
    else:
        lines.append("| UNKNOWN | 0 | n/a |")
    lines += [
        "",
        "## Holdings audit",
        "",
        "| Ticker | Weight % | Data confidence | Conclusion risk | Artifact status | Manual review |",
        "|---|---:|---|---|---|---|",
    ]
    for row in package.get("holdings") or []:
        review = "<br>".join(row.get("manual_review_items") or []) or "n/a"
        lines.append(f"| `{row.get('ticker')}` | {row.get('weight_pct', 0)} | {row.get('data_confidence_level', 'UNKNOWN')} | {row.get('conclusion_risk_level', 'UNKNOWN')} | {row.get('artifact_status', 'UNKNOWN')} | {review} |")
    lines += ["", "## Attribution Lite", "", "| Field | Value |", "|---|---|" ]
    attribution = package.get("attribution_lite") or {}
    lines.append(f"| Status | `{attribution.get('status', 'UNKNOWN')}` |")
    lines.append(f"| Reason code | `{attribution.get('reason_code', 'UNKNOWN')}` |")
    lines.append(f"| Total estimated market value | `{attribution.get('total_current_value', 'UNKNOWN')}` |")
    lines += ["", "## Manual review items", ""]
    for item in package.get("manual_review_items") or []:
        lines.append(f"- {item}")
    if not package.get("manual_review_items"):
        lines.append("- n/a")
    lines += ["", "## Limitations", ""]
    for limitation in package.get("limitations") or []:
        lines.append(f"- {limitation}")
    return "\n".join(lines) + FOOTER


def write_portfolio_audit_artifacts(package: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    portfolio_id = _safe_filename(str(package.get("portfolio_id") or "portfolio"))
    json_path = out / f"{portfolio_id}_portfolio_audit.json"
    md_path = out / f"{portfolio_id}_portfolio_audit_report.md"
    json_path.write_text(json.dumps(package, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_portfolio_audit_report_md(package), encoding="utf-8")
    return {"portfolio_audit_json": str(json_path), "portfolio_audit_report_md": str(md_path)}


def _audit_holding(row: Mapping[str, Any], audit: Mapping[str, Any] | None, business_risk: Mapping[str, Any] | None, thesis: Mapping[str, Any] | None, sensitivity: Mapping[str, Any] | None) -> dict[str, Any]:
    ticker = str(row.get("ticker") or "UNKNOWN").upper()
    weight = _weight(row)
    artifact_status = "KNOWN" if audit else "UNKNOWN"
    data_level = _nested(audit, "data_confidence", "level") or _nested(audit, "data_confidence", "confidence_grade") or "UNKNOWN"
    risk_level = _nested(audit, "conclusion_risk", "risk_level") or "UNKNOWN"
    app_status = _nested(audit, "model_applicability", "status") or "UNKNOWN"
    allowed = _nested(audit, "model_applicability", "allowed_score_usage") or "UNKNOWN"
    thesis_status = (thesis or {}).get("thesis_status") or "UNKNOWN"
    fragility = _nested(sensitivity, "fragility", "fragility_level") or "UNKNOWN"
    red_fail = _nested(business_risk, "red_flags_summary", "fail_count")
    provider_degraded = bool((audit or {}).get("provider_degradation_visible"))
    manual_items = []
    if not audit and ticker != "CASH":
        manual_items.append("Audit artifact missing; exposure treated as UNKNOWN.")
    if app_status in {"DEGRADED", "NOT_APPLICABLE", "UNKNOWN"} and ticker != "CASH":
        manual_items.append(f"Model applicability requires review: {app_status}/{allowed}.")
    if risk_level in {"HIGH", "UNKNOWN"} and ticker != "CASH":
        manual_items.append(f"Conclusion risk is {risk_level}.")
    if provider_degraded:
        manual_items.append("Provider degradation visible for this holding.")
    if red_fail not in (None, 0):
        manual_items.append(f"Business-risk red flags present: {red_fail}.")
    if thesis_status in {"BROKEN", "WATCH", "UNKNOWN"} and ticker != "CASH":
        manual_items.append(f"Thesis status requires review: {thesis_status}.")
    return {
        "ticker": ticker,
        "weight": weight,
        "weight_pct": _pct(weight),
        "current_value": row.get("current_value"),
        "sector": row.get("sector") or "UNKNOWN",
        "factor": row.get("factor") or "UNKNOWN",
        "thesis_id": row.get("thesis_id") or (thesis or {}).get("thesis_type") or "UNKNOWN",
        "macro_exposure": list(row.get("macro_exposure") or []),
        "artifact_status": artifact_status,
        "data_confidence_level": data_level,
        "data_confidence_score": CONFIDENCE_SCORE.get(str(data_level).upper()),
        "model_applicability_status": app_status,
        "allowed_score_usage": allowed,
        "conclusion_risk_level": risk_level,
        "conclusion_risk_score": RISK_SCORE.get(str(risk_level).upper()),
        "thesis_status": thesis_status,
        "sensitivity_fragility_level": fragility,
        "business_red_flags_count": red_fail if red_fail is not None else "UNKNOWN",
        "provider_degradation_visible": provider_degraded,
        "source_quality": (audit or business_risk or thesis or sensitivity or {}).get("source_quality") or "UNKNOWN",
        "source_class": (audit or business_risk or thesis or sensitivity or {}).get("source_class") or "operator_curated_portfolio_input",
        "valuation_date": (audit or sensitivity or {}).get("valuation_date"),
        "manual_review_items": manual_items,
    }


def _concentration(rows: Sequence[Mapping[str, Any]], field: str, *, ignore: set[Any] | None = None) -> dict[str, Any]:
    ignore = ignore or set()
    weights: dict[str, float] = {}
    for row in rows:
        key = row.get(field) or "UNKNOWN"
        if key in ignore or str(key).strip() == "":
            continue
        weights[str(key)] = weights.get(str(key), 0.0) + _weight(row)
    total = sum(weights.values())
    if not weights or total <= 0:
        return {"status": "UNKNOWN", "reason_code": "PORTFOLIO_COMPONENT_UNKNOWN", "hhi": 0.0, "top_bucket": "UNKNOWN", "top_weight_pct": 0.0, "buckets": []}
    buckets = sorted(({"bucket": k, "weight_pct": _pct(v), "weight": v} for k, v in weights.items()), key=lambda x: (-x["weight"], x["bucket"]))
    hhi = sum((v / total) ** 2 for v in weights.values())
    top = buckets[0]
    reason = "PORTFOLIO_CONCENTRATION_HIGH" if top["weight"] / total >= 0.5 or hhi >= 0.35 else "PORTFOLIO_CONCENTRATION_COMPUTED"
    return {"status": "PASS_WITH_LIMITATIONS" if reason.endswith("HIGH") else "PASS", "reason_code": reason, "hhi": round(hhi, 4), "top_bucket": top["bucket"], "top_weight_pct": top["weight_pct"], "buckets": buckets}


def _macro_sensitivity_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    exposures: dict[str, dict[str, Any]] = {}
    for row in rows:
        for exp in row.get("macro_exposure") or []:
            entry = exposures.setdefault(str(exp), {"exposure": str(exp), "weight": 0.0, "tickers": []})
            entry["weight"] += _weight(row)
            entry["tickers"].append(str(row.get("ticker")))
    items = sorted(({"exposure": k, "weight_pct": _pct(v["weight"]), "weight": v["weight"], "tickers": sorted(set(v["tickers"]))} for k, v in exposures.items()), key=lambda x: (-x["weight"], x["exposure"]))
    if not items:
        return {"status": "UNKNOWN", "reason_code": "PORTFOLIO_MACRO_EXPOSURE_UNKNOWN", "exposures": []}
    top = items[0]
    return {"status": "PASS_WITH_LIMITATIONS", "reason_code": "PORTFOLIO_MACRO_EXPOSURE_COMPUTED", "top_exposure": top["exposure"], "top_weight_pct": top["weight_pct"], "exposures": items}


def _attribution_lite(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [r.get("current_value") for r in rows if _num(r.get("current_value")) is not None]
    if not values:
        return {"status": "UNKNOWN", "reason_code": "PORTFOLIO_ATTRIBUTION_INPUTS_MISSING", "total_current_value": None, "holdings_with_value_count": 0}
    total = sum(float(v) for v in values)
    contributions = []
    for row in rows:
        value = _num(row.get("current_value"))
        if value is None:
            continue
        contributions.append({"ticker": row.get("ticker"), "current_value": value, "weight_by_value_pct": _pct(value / total if total else 0.0)})
    return {"status": "PASS_WITH_LIMITATIONS", "reason_code": "PORTFOLIO_ATTRIBUTION_LITE_COMPUTED", "total_current_value": round(total, 4), "holdings_with_value_count": len(contributions), "contributions": contributions}


def _portfolio_manual_review_items(rows: Sequence[Mapping[str, Any]], sector: Mapping[str, Any], factor: Mapping[str, Any], thesis: Mapping[str, Any], macro: Mapping[str, Any], unknown_weight: float, degraded_weight: float, data_score: float | None, risk_score: float | None) -> list[str]:
    items: list[str] = []
    if unknown_weight > 0:
        items.append(f"Unknown artifact exposure is {_pct(unknown_weight)}% of portfolio weight.")
    if degraded_weight > 0:
        items.append(f"Provider-degraded exposure is {_pct(degraded_weight)}% of portfolio weight.")
    if data_score is None or data_score < 0.6:
        items.append("Weighted data confidence is below MEDIUM or unavailable.")
    if risk_score is None or risk_score >= 0.5:
        items.append("Weighted conclusion risk is MEDIUM/HIGH or unavailable.")
    for name, obj in (("sector", sector), ("factor", factor), ("thesis", thesis)):
        if obj.get("reason_code") == "PORTFOLIO_CONCENTRATION_HIGH":
            items.append(f"High {name} concentration: {obj.get('top_bucket')} at {obj.get('top_weight_pct')}%.")
    if macro.get("status") == "UNKNOWN":
        items.append("Macro exposure labels are missing; macro sensitivity map is UNKNOWN.")
    for row in rows:
        for item in row.get("manual_review_items") or []:
            items.append(f"{row.get('ticker')}: {item}")
    return items


def _looks_like(obj: Mapping[str, Any], kind: str) -> bool:
    schema = str(obj.get("schema_version") or "")
    if kind == "audit":
        return schema.startswith("audit_summary") or "data_confidence" in obj and "model_applicability" in obj
    if kind == "business_risk":
        return schema.startswith("business_risk_package") or "red_flags_summary" in obj
    if kind == "thesis":
        return schema.startswith("thesis_status") or "thesis_status" in obj
    if kind == "sensitivity":
        return schema.startswith("sensitivity_summary") or "fragility" in obj
    return False


def _normalize_missing_weights(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known = [r for r in rows if r.get("weight") is not None]
    if known:
        return rows
    values = [r for r in rows if _num(r.get("current_value")) is not None]
    if values:
        total = sum(float(r["current_value"]) for r in values)
        for r in rows:
            if _num(r.get("current_value")) is not None and total:
                r["weight"] = float(r["current_value"]) / total
            else:
                r["weight"] = 0.0
        return rows
    non_cash = [r for r in rows if r.get("ticker") != "CASH"]
    equal = 1.0 / len(non_cash) if non_cash else 0.0
    for r in rows:
        r["weight"] = 0.0 if r.get("ticker") == "CASH" else equal
    return rows


def _parse_weight(value: Any) -> float | None:
    n = _num(value)
    if n is None:
        return None
    return n / 100.0 if n > 1.0 else n


def _weight(row: Mapping[str, Any]) -> float:
    n = _num(row.get("weight"))
    return max(0.0, float(n or 0.0))


def _weighted_average(values: Iterable[tuple[Any, float]]) -> float | None:
    total = 0.0
    weighted = 0.0
    for value, weight in values:
        if value is None:
            continue
        w = float(weight or 0.0)
        if w <= 0:
            continue
        weighted += float(value) * w
        total += w
    if total <= 0:
        return None
    return weighted / total


def _confidence_level(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    if score >= 0.8:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "UNKNOWN"


def _risk_level(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    if score >= 0.75:
        return "HIGH"
    if score >= 0.3:
        return "MEDIUM"
    return "LOW"


def _aggregate_source_quality(rows: Sequence[Mapping[str, Any]]) -> str:
    qualities = [str(r.get("source_quality") or "UNKNOWN") for r in rows]
    if not qualities:
        return "UNKNOWN"
    best = min(qualities, key=lambda q: QUALITY_RANK.get(q, 0))
    # Return the weakest material quality to avoid overstating confidence.
    return best


def _aggregate_source_class(rows: Sequence[Mapping[str, Any]]) -> str:
    classes = sorted({str(r.get("source_class") or "UNKNOWN") for r in rows if r.get("source_class")})
    return ",".join(classes) if classes else "operator_curated_portfolio_input"


def _nested(obj: Mapping[str, Any] | None, *keys: str) -> Any:
    cur: Any = obj or {}
    for key in keys:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


def _first_non_empty(values: Iterable[Any]) -> Any:
    for value in values:
        if value not in (None, "", "UNKNOWN"):
            return value
    return None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _pct(value: float | None) -> float:
    return round((value or 0.0) * 100.0, 4)


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None and str(value).strip() else "UNKNOWN"


def _split_tokens(value: Any) -> list[str]:
    text = str(value or "").replace(";", ",").replace("|", ",")
    return [tok.strip() for tok in text.split(",") if tok.strip()]


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned or "portfolio"
