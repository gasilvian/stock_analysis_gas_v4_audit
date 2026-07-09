"""Render SEC mapping reports for audit review."""
from __future__ import annotations

from typing import Any

FOOTER = "_Internal/personal/educational use only. Not investment advice._"


def mapping_report_md(snapshot: dict[str, Any]) -> str:
    report = snapshot.get("mapping_report") or {}
    lines = [
        f"# SEC CompanyFacts Mapping Report — {snapshot.get('ticker')}",
        "",
        f"Status: `{report.get('status') or snapshot.get('status')}`",
        f"CIK: `{snapshot.get('cik')}`",
        f"Source: `{snapshot.get('source_path')}`",
        f"Normalized at: `{snapshot.get('normalized_at')}`",
        "",
        "## Mapped fields",
        "",
    ]
    mapped = report.get("mapped_fields") or []
    if mapped:
        lines.extend(f"- `{f}`" for f in mapped)
    else:
        lines.append("- none")
    lines += ["", "## Unmapped / UNKNOWN fields", ""]
    unmapped = report.get("unmapped_fields") or []
    if unmapped:
        for item in unmapped:
            lines.append(f"- `{item.get('field')}` → `{item.get('reason_code')}`")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Governance",
        "",
        f"- Source quality: `{report.get('source_quality')}`",
        f"- Source class: `{report.get('source_class')}`",
        f"- Source tier: `{report.get('source_tier')}`",
        f"- UNKNOWN policy: {report.get('unknown_policy')}",
        "",
        FOOTER,
    ]
    return "\n".join(lines) + "\n"
