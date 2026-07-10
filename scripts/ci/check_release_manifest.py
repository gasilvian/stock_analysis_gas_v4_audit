#!/usr/bin/env python3
"""Governance gate for P0.14 MVP release manifest/report artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

FORBIDDEN = [
    " BUY ",
    " SELL ",
    " HOLD ",
    "BUY/SELL/HOLD",
    "price target",
    "target price",
    "recommendation to",
    "rebalance into",
]


def _find_manifest(base: Path) -> Path | None:
    if base.is_file():
        return base
    candidates = sorted(base.rglob("*_release_manifest.json"))
    return candidates[0] if candidates else None


def main(argv: list[str]) -> int:
    base = Path(argv[1]) if len(argv) > 1 else Path("out/p14_ci")
    manifest_path = _find_manifest(base)
    if not manifest_path or not manifest_path.exists():
        print(f"FAIL: release manifest not found under {base}", file=sys.stderr)
        return 1
    obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if obj.get("schema_version") != "release_manifest.v0.1":
        failures.append("unexpected schema_version")
    if obj.get("sprint") != "v4.0-p0.14":
        failures.append("unexpected sprint")
    if obj.get("not_investment_advice") is not True:
        failures.append("not_investment_advice must be true")
    guardrails = obj.get("scope_guardrails") or {}
    for key in [
        "not_investment_advice",
        "output_schema_unchanged_policy",
        "unknown_policy_preserved",
        "provider_degradation_visible_policy",
        "recommendation_language_absent",
    ]:
        if guardrails.get(key) is not True:
            failures.append(f"scope_guardrails.{key} must be true")
    # P2.7: the template-era assertion pinned NOT_READY forever. Rule 19 says
    # NOT_READY *until* curated sources are populated and reviewed — which is
    # now a live, verifiable condition. The gate therefore RECOMPUTES
    # readiness (legal scope + source registry, production scope) and
    # requires the manifest to match it exactly: a manifest claiming PASS
    # while the live evaluation says NOT_READY (or vice versa) is a
    # falsification and fails the gate.
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from sws_engine.governance.legal_scope import validate_legal_scope
    from sws_engine.sources.real_sources import validate_source_registry
    _root = Path(__file__).resolve().parents[2]
    _legal = validate_legal_scope(str(_root / "config/legal_scope.yaml")).as_dict()
    _sources = validate_source_registry(str(_root / "config/source_registry.yaml"),
                                        require_production=True).as_dict()
    expected_readiness = "PASS" if _legal["status"] == "PASS" and _sources["status"] == "PASS" else "NOT_READY"
    if guardrails.get("production_readiness") != expected_readiness:
        failures.append(
            f"production_readiness mismatch: manifest says {guardrails.get('production_readiness')!r} "
            f"but live evaluation (legal scope + source registry) says {expected_readiness!r}")
    if not obj.get("capabilities"):
        failures.append("capabilities missing")
    summary = obj.get("capability_summary") or {}
    if summary.get("unknown_or_missing"):
        failures.append("required capability files missing")
    if not obj.get("known_limitations"):
        failures.append("known_limitations missing")
    if not obj.get("manual_review_items"):
        failures.append("manual_review_items should keep production-readiness limitation visible")
    text = f" {json.dumps(obj, sort_keys=True)} "
    for token in FORBIDDEN:
        if token in text:
            failures.append(f"forbidden recommendation token detected in manifest: {token.strip()}")
    report_paths = sorted(manifest_path.parent.rglob("*_release_report.md"))
    if not report_paths:
        failures.append("release report markdown missing")
    for report in report_paths:
        md = f" {report.read_text(encoding='utf-8')} "
        if "Not investment advice" not in md:
            failures.append(f"{report}: missing not-investment-advice footer")
        if "What remains UNKNOWN or limited" not in md:
            failures.append(f"{report}: missing UNKNOWN/limitations section")
        for token in FORBIDDEN:
            if token in md:
                failures.append(f"{report}: forbidden recommendation token detected: {token.strip()}")
    if failures:
        for failure in failures:
            print("FAIL:", failure, file=sys.stderr)
        return 1
    print(f"PASS: release manifest guardrails OK for {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
