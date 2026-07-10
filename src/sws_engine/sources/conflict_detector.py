"""Source conflict detector runtime (B5 / P1.6).

The SEC payload merge (P1.3b) started recording conflicts at merge time with
a hardcoded, documented sec_precedence. This module generalizes that into the
registry-driven mechanism required by the product doctrine:

- the precedence chain lives in ``config/source_registry.yaml`` (top-level
  ``precedence`` list, highest priority first) — operator-auditable, not
  buried in code;
- a conflict between two sources is resolvable ONLY when both sources appear
  in the chain; otherwise the field must become UNKNOWN
  (``SOURCE_CONFLICT_UNRESOLVED``), never a silent pick;
- every payload can be turned into a standalone conflict-report artifact
  (JSON + MD) listing each conflict, its resolution, and whether the
  divergence is material enough to require manual review.

Materiality: numeric conflicts with relative difference above
``material_threshold`` (default 5%) are flagged
``SOURCE_CONFLICT_MATERIAL_REVIEW_REQUIRED`` — the resolution is still the
documented precedence, but the operator is told the sources disagree enough
to matter.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY_PATH = "config/source_registry.yaml"
# Fallback mirrors the registry section so behavior is identical when a
# registry without the section is supplied (older snapshots).
DEFAULT_PRECEDENCE = [
    "manual_override", "manual_estimates_pack", "sec_companyfacts",
    "curated_rates", "curated_averages", "yfinance",
]
DEFAULT_MATERIAL_THRESHOLD = 0.05


def load_precedence(registry_path: str | Path = DEFAULT_REGISTRY_PATH) -> list[str]:
    try:
        registry = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return list(DEFAULT_PRECEDENCE)
    chain = registry.get("precedence")
    if isinstance(chain, list) and chain:
        return [str(x) for x in chain]
    return list(DEFAULT_PRECEDENCE)


def _normalize_source(source: str | None) -> str:
    s = str(source or "").lower()
    if s.startswith("yfinance"):
        return "yfinance"
    return s


def resolve_precedence(source_a: str | None, source_b: str | None,
                       precedence: list[str] | None = None) -> str | None:
    """Return the winning source id, or None when no rule covers the pair.

    None is the doctrine-critical outcome: the caller must set the field
    UNKNOWN rather than choose.
    """
    chain = precedence if precedence is not None else list(DEFAULT_PRECEDENCE)
    a, b = _normalize_source(source_a), _normalize_source(source_b)
    if a not in chain or b not in chain:
        return None
    return source_a if chain.index(a) <= chain.index(b) else source_b


def resolve_field(
    field: str,
    candidates: dict[str, dict[str, Any]],
    *,
    precedence: list[str] | None = None,
    material_threshold: float = DEFAULT_MATERIAL_THRESHOLD,
) -> dict[str, Any]:
    """Resolve one field across candidate sources.

    ``candidates`` maps source id -> {"value": ..., "lineage": {...}}.
    Returns {"status", "value", "winner", "conflicts": [...]}:
    - single candidate -> RESOLVED trivially;
    - multiple agreeing candidates -> RESOLVED, highest-precedence wins the
      lineage attribution;
    - disagreeing candidates all in the chain -> RESOLVED with conflict
      records (resolution=precedence:<winner>), material flag when the
      relative diff exceeds the threshold;
    - any disagreeing candidate outside the chain -> UNKNOWN
      (SOURCE_CONFLICT_UNRESOLVED), value None, nothing picked.
    """
    chain = precedence if precedence is not None else list(DEFAULT_PRECEDENCE)
    sources = list(candidates)
    if not sources:
        return {"status": "UNKNOWN", "value": None, "winner": None, "conflicts": [],
                "reason_code": "NO_CANDIDATES"}
    ordered = sorted(
        sources,
        key=lambda s: chain.index(_normalize_source(s)) if _normalize_source(s) in chain else len(chain))
    winner = ordered[0]
    conflicts: list[dict[str, Any]] = []
    unresolved = False
    win_value = candidates[winner].get("value")
    for other in ordered[1:]:
        other_value = candidates[other].get("value")
        if other_value is None or other_value == win_value:
            continue
        rel = None
        if isinstance(win_value, (int, float)) and isinstance(other_value, (int, float)) \
                and not isinstance(win_value, bool) and not isinstance(other_value, bool):
            denom = max(abs(float(win_value)), abs(float(other_value)), 1e-12)
            rel = abs(float(win_value) - float(other_value)) / denom
        rule = resolve_precedence(winner, other, chain)
        record = {
            "field": field, "source_a": winner, "value_a": win_value,
            "source_b": other, "value_b": other_value,
            "relative_diff": round(rel, 6) if rel is not None else None,
        }
        if rule is None:
            unresolved = True
            record["resolution"] = "unresolved_no_precedence_rule"
        else:
            record["resolution"] = f"precedence:{rule}"
            record["material_review_required"] = bool(rel is not None and rel > material_threshold)
        conflicts.append(record)
    if unresolved:
        return {"status": "UNKNOWN", "value": None, "winner": None,
                "conflicts": conflicts, "reason_code": "SOURCE_CONFLICT_UNRESOLVED"}
    return {"status": "RESOLVED", "value": win_value, "winner": winner,
            "conflicts": conflicts,
            "reason_code": "SOURCE_CONFLICTS_RESOLVED_BY_PRECEDENCE" if conflicts else "NO_CONFLICT"}


def build_conflict_report(
    payload: dict[str, Any],
    *,
    material_threshold: float = DEFAULT_MATERIAL_THRESHOLD,
) -> dict[str, Any]:
    """Standalone conflict-report artifact from a payload's recorded conflicts."""
    recorded = list(payload.get("source_conflicts") or [])
    material: list[dict[str, Any]] = []
    for record in recorded:
        rel = record.get("relative_diff")
        record = dict(record)
        record["material_review_required"] = bool(
            isinstance(rel, (int, float)) and rel > material_threshold)
        if record["material_review_required"]:
            material.append(record)
    unresolved = [r for r in recorded if str(r.get("resolution", "")).startswith("unresolved")]
    if unresolved:
        status, reason = "FAIL", "SOURCE_CONFLICT_UNRESOLVED"
    elif material:
        status, reason = "PASS_WITH_LIMITATIONS", "SOURCE_CONFLICT_MATERIAL_REVIEW_REQUIRED"
    elif recorded:
        status, reason = "PASS_WITH_LIMITATIONS", "SOURCE_CONFLICTS_RESOLVED_BY_PRECEDENCE"
    else:
        status, reason = "PASS", "SOURCE_CONFLICTS_NONE"
    conflicts_out = []
    for record in recorded:
        rel = record.get("relative_diff")
        out = dict(record)
        out["material_review_required"] = bool(isinstance(rel, (int, float)) and rel > material_threshold)
        conflicts_out.append(out)
    return {
        "schema_version": "source_conflict_report.v1",
        "status": status,
        "reason_code": reason,
        "ticker": payload.get("ticker"),
        "valuation_date": payload.get("valuation_date"),
        "provider_profile": payload.get("provider_profile"),
        "precedence_chain": load_precedence(),
        "material_threshold": material_threshold,
        "conflicts_count": len(recorded),
        "material_count": len(material),
        "unresolved_count": len(unresolved),
        "conflicts": conflicts_out,
        "manual_review_required": bool(material or unresolved),
        "not_investment_advice": True,
    }


def render_conflict_report_md(report: dict[str, Any]) -> str:
    lines = [
        f"# Source Conflict Report — {report.get('ticker')}",
        "",
        f"- Status: `{report['status']}` / `{report['reason_code']}`",
        f"- Conflicts: {report['conflicts_count']} "
        f"(material: {report['material_count']}, unresolved: {report['unresolved_count']})",
        f"- Precedence chain: {' > '.join(report['precedence_chain'])}",
        f"- Material threshold: {report['material_threshold']:.1%}",
        "",
    ]
    if report["conflicts"]:
        lines.append("| Field | Base/source A | SEC/source B | Rel. diff | Resolution | Manual review |")
        lines.append("|---|---|---|---|---|---|")
        for c in report["conflicts"]:
            a = f"{c.get('base_provider') or c.get('source_a')}: {c.get('base_value', c.get('value_a'))}"
            b = f"{c.get('source_b', 'sec_companyfacts')}: {c.get('sec_value', c.get('value_b'))}"
            rel = c.get("relative_diff")
            lines.append(
                f"| {c['field']} | {a} | {b} | "
                f"{'' if rel is None else format(rel, '.2%')} | {c.get('resolution')} | "
                f"{'YES' if c.get('material_review_required') else 'no'} |")
    else:
        lines.append("No conflicts recorded between sources for this payload.")
    lines += ["", "Not investment advice. Not the live Simply Wall St model.", ""]
    return "\n".join(lines)


def write_conflict_report(
    payload: dict[str, Any],
    output_dir: str | Path,
    *,
    material_threshold: float = DEFAULT_MATERIAL_THRESHOLD,
) -> dict[str, Any]:
    report = build_conflict_report(payload, material_threshold=material_threshold)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ticker = str(report.get("ticker") or "UNKNOWN")
    json_path = out / f"{ticker}_source_conflicts.json"
    md_path = out / f"{ticker}_source_conflicts_report.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_conflict_report_md(report), encoding="utf-8")
    return {"report": report, "paths": {
        "source_conflicts_json": str(json_path),
        "source_conflicts_report_md": str(md_path),
    }}
