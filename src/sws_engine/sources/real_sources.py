"""Production source registry and real-data readiness gates.

The engine can run on synthetic construction data, but a daily internal product
needs explicit source ownership and proof that required files/providers are real
or curated. This module validates a source registry and generates a readiness
report without fetching the internet.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

TEMPLATE_MARKERS = ("template", "synthetic", "syn-")
READY_STATUSES = {"implemented", "implemented_optional", "populated", "real_curated", "live_available"}
NOT_READY_STATUSES = {"template_needs_population", "missing", "synthetic", "unknown"}


@dataclass
class SourceRegistryReport:
    status: str
    registry_path: str
    checked_at: str
    source_count: int
    ready_count: int
    blocking_issues: list[str]
    warnings: list[str]
    sources: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "registry_path": self.registry_path,
            "checked_at": self.checked_at,
            "source_count": self.source_count,
            "ready_count": self.ready_count,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "sources": self.sources,
        }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_source_registry(path: str | Path = "config/source_registry.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"metadata": {}, "sources": [], "_missing_file": str(path)}
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"metadata": {}, "sources": []}


def _looks_template(path: str | None, status: str | None) -> bool:
    hay = f"{path or ''} {status or ''}".lower()
    return any(m in hay for m in TEMPLATE_MARKERS)


def _file_exists(path: str | None) -> bool | None:
    if not path:
        return None
    return Path(path).exists()


def _file_contains_template_marker(path: str | None, max_bytes: int = 65536) -> bool | None:
    """Return whether a candidate real-source file still self-identifies as sample/template/synthetic.

    Production readiness must not pass merely because a file exists at the
    curated target path. Operators sometimes copy sample files into the real
    target path during setup; this guard keeps such files NOT_READY until the
    sample/template markers are removed and replaced with genuine source
    metadata.
    """
    if not path:
        return None
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")[:max_bytes].lower()
    except OSError:
        return None
    markers = (
        "sample_only",
        "sample only",
        "template",
        "synthetic",
        "not real data",
        "demo_fixture",
        "example only",
    )
    return any(marker in content for marker in markers)


def validate_source_registry(path: str | Path = "config/source_registry.yaml", *, require_production: bool = False) -> SourceRegistryReport:
    registry = load_source_registry(path)
    issues: list[str] = []
    warnings: list[str] = []
    evaluated: list[dict[str, Any]] = []
    if registry.get("_missing_file"):
        issues.append(f"source registry missing: {registry['_missing_file']}")

    for src in registry.get("sources", []) or []:
        row = dict(src)
        sid = row.get("id") or "<missing-id>"
        status = str(row.get("status") or "unknown")
        path_value = row.get("replacement_target_path") or row.get("path")
        exists = _file_exists(path_value)
        file_has_marker = _file_contains_template_marker(path_value)
        is_template = _looks_template(str(path_value) if path_value else None, status) or bool(file_has_marker)
        required = bool(row.get("required_for_production_real_data")) if require_production else bool(row.get("required_for_internal_daily_run"))
        live_provider = row.get("source_type") == "live_provider" and status in READY_STATUSES

        ready = False
        if live_provider:
            ready = True
        elif exists is True and not is_template and status in READY_STATUSES:
            ready = True
        elif exists is True and not is_template and status not in NOT_READY_STATUSES:
            # Allow user-curated files that have not been labelled yet, but warn.
            ready = True
            warnings.append(f"{sid}: file exists and is non-template but status={status!r}; consider setting status=real_curated")

        if required and not ready:
            issues.append(f"{sid}: required source is not production-ready")
        if is_template and required:
            warnings.append(f"{sid}: template/synthetic marker detected; replace with real curated file before production use")
        if exists is False and row.get("source_type") != "live_provider" and required:
            warnings.append(f"{sid}: expected file missing at {path_value}")

        row.update({
            "evaluated_required": required,
            "evaluated_path": path_value,
            "file_exists": exists,
            "file_contains_template_marker": file_has_marker,
            "looks_template_or_synthetic": is_template,
            "ready": ready,
        })
        evaluated.append(row)

    ready_count = sum(1 for r in evaluated if r.get("ready"))
    status = "PASS" if not issues else "NOT_READY"
    return SourceRegistryReport(
        status=status,
        registry_path=str(path),
        checked_at=_now(),
        source_count=len(evaluated),
        ready_count=ready_count,
        blocking_issues=issues,
        warnings=warnings,
        sources=evaluated,
    )


def _read_watchlist(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def populate_real_sources(*, watchlist_path: str, output_dir: str = "data/real_sources", valuation_date: str | None = None, refresh: bool = False) -> dict[str, Any]:
    """Populate real-source working folders from yfinance live provider.

    This function is intentionally conservative: it writes raw snapshots and
    mapped payloads, and records per-ticker failures. It does not claim SWS
    faithfulness and does not overwrite curated rate/universe files.
    """
    rows = _read_watchlist(watchlist_path)
    base = Path(output_dir)
    snapshots_dir = base / "snapshots"
    payloads_dir = base / "payloads"
    manifests_dir = base / "manifests"
    for d in (snapshots_dir, payloads_dir, manifests_dir):
        d.mkdir(parents=True, exist_ok=True)

    try:
        from sws_engine.providers.yfinance_live import YFinanceLiveProvider
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": f"live provider unavailable: {exc}",
            "hint": "Install live extra: pip install -e \".[live]\"",
            "watchlist_path": watchlist_path,
        }

    provider = YFinanceLiveProvider(refresh=refresh)
    result = {"PASS": [], "FAIL": [], "SKIPPED": []}
    for row in rows:
        ticker = (row.get("ticker") or "").strip()
        if not ticker:
            result["SKIPPED"].append({"ticker": None, "reason": "missing ticker"})
            continue
        try:
            snapshot = provider.fetch_raw_snapshot(ticker)
            payload = provider.build_payload(
                ticker,
                valuation_date=valuation_date,
                market=row.get("market") or row.get("country"),
                industry=row.get("industry"),
            )
            snapshot_path = snapshots_dir / f"{ticker}_snapshot.json"
            payload_path = payloads_dir / f"{ticker}_payload.json"
            snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            result["PASS"].append({
                "ticker": ticker,
                "snapshot_path": str(snapshot_path),
                "payload_path": str(payload_path),
                "warnings_count": len(payload.get("builder_warnings") or payload.get("warnings") or []),
            })
        except Exception as exc:
            result["FAIL"].append({"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"})

    manifest = {
        "status": "PASS_WITH_LIMITATIONS" if result["PASS"] else "FAIL",
        "created_at": _now(),
        "watchlist_path": watchlist_path,
        "valuation_date": valuation_date,
        "provider_profile": "yfinance_pragmatic",
        "note": "Live yfinance data is pragmatic/degraded and may produce UNKNOWN checks. This manifest is not investment advice.",
        "result": result,
    }
    manifest_path = manifests_dir / f"real_source_population_{valuation_date or _now().replace(':', '')}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest
