"""Pipeline orchestration: run_company_analysis (runbook.md section 2)."""
import json
import os
from datetime import datetime, timezone

from sws_engine.checks.engine import run_all_checks
from sws_engine.config.assumptions_loader import load_assumptions, run_snapshot
from sws_engine.contracts.input_contract import get_num, normalize_input
from sws_engine.contracts.lineage import build_lineage
from sws_engine.contracts.output_contract import build_output
from sws_engine.contracts.schema_validator import validate_output
from sws_engine.providers.yfinance_pragmatic import get_provider
from sws_engine.scoring.axis_scores import compute_axis_scores
from sws_engine.valuation.resolve import resolve_valuation
from sws_engine.warnings.provider_degradation import collect_warnings


def run_company_analysis(input_payload: dict, assumptions_path: str,
                         schema_path: str, snapshot_dir: str = None) -> dict:
    """Runs the full v3.1 MVP pipeline and returns schema-valid output JSON.

    Strict mode: missing inputs are never autofilled; dependent checks
    return UNKNOWN and fair_value stays null unless manually supplied.
    """
    payload = normalize_input(input_payload)
    assumptions = load_assumptions(assumptions_path)
    frozen_assumptions = run_snapshot(assumptions)

    provider = get_provider(payload["provider_profile"])
    provider_result = provider.prepare(payload)
    payload = provider_result.payload

    (fair_value, discount_pct, model, variant, model_class,
     _val_details, val_warnings) = resolve_valuation(payload, frozen_assumptions)

    checks = run_all_checks(payload, frozen_assumptions,
                            provider_result.field_quality, fair_value)
    scores = compute_axis_scores(checks)
    lineage = build_lineage(payload, frozen_assumptions.get("metadata", {}))
    warnings = collect_warnings(payload, provider_result, checks) + val_warnings

    output = build_output(
        ticker=payload["ticker"], exchange=payload["exchange"],
        valuation_date=payload["valuation_date"],
        provider_profile=payload["provider_profile"],
        valuation_model=model, valuation_variant=variant,
        valuation_model_source_class=model_class,
        fair_value=fair_value, price=get_num(payload, "price"),
        discount_pct=discount_pct, scores=scores, checks=checks,
        lineage=lineage, warnings=warnings,
    )
    validate_output(output, schema_path)

    if snapshot_dir:
        os.makedirs(snapshot_dir, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snap = {
            "run_at_utc": stamp,
            "assumptions_snapshot": frozen_assumptions,
            "output": output,
        }
        path = os.path.join(snapshot_dir,
                            f"{payload['ticker']}_{payload['valuation_date']}_{stamp}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2)
    return output
