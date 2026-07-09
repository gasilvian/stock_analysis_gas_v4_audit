"""Versioned rates/FX source registry (Plan D).

The engine can run with synthetic curated construction files, but operational
use needs explicit source metadata for 10Y bond series, ERP tables and EOD FX.
This module validates that the files are versioned and reports whether a file
is synthetic/template/real-curated. It does not fetch commercial data.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SourceStatus:
    path: str
    exists: bool
    source: str | None = None
    as_of: str | None = None
    kind: str | None = None
    warnings: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "source": self.source,
            "as_of": self.as_of,
            "kind": self.kind,
            "warnings": self.warnings or [],
        }


def _classify_source(source: str | None, path: str) -> str:
    s = (source or "").lower()
    p = path.lower()
    if "synthetic" in s or "synthetic" in p:
        return "synthetic_curated"
    if "template" in s or "template" in p:
        return "template"
    if source:
        return "real_or_curated"
    return "unknown"


def inspect_bond_csv(path: str) -> dict:
    warnings: list[str] = []
    p = Path(path)
    if not p.exists():
        return SourceStatus(path, False, warnings=["missing bond CSV"]).as_dict()
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    required = {"country", "date", "yield_10y"}
    missing_cols = sorted(required - set(reader.fieldnames or []))
    if missing_cols:
        warnings.append(f"missing columns: {missing_cols}")
    source = rows[0].get("source") if rows and "source" in (reader.fieldnames or []) else None
    as_of = max((r.get("date", "") for r in rows), default=None)
    if not rows:
        warnings.append("no observations")
    return SourceStatus(path, True, source=source, as_of=as_of, kind=_classify_source(source, path), warnings=warnings).as_dict()


def inspect_erp_json(path: str) -> dict:
    warnings: list[str] = []
    p = Path(path)
    if not p.exists():
        return SourceStatus(path, False, warnings=["missing ERP JSON"]).as_dict()
    with p.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not data.get("countries"):
        warnings.append("countries table missing/empty")
    source = data.get("source")
    return SourceStatus(path, True, source=source, as_of=data.get("as_of"), kind=_classify_source(source, path), warnings=warnings).as_dict()


def inspect_fx_csv(path: str) -> dict:
    warnings: list[str] = []
    p = Path(path)
    if not p.exists():
        return SourceStatus(path, False, warnings=["missing FX CSV"]).as_dict()
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    required = {"pair", "date", "rate"}
    missing_cols = sorted(required - set(reader.fieldnames or []))
    if missing_cols:
        warnings.append(f"missing columns: {missing_cols}")
    source = rows[0].get("source") if rows and "source" in (reader.fieldnames or []) else None
    as_of = max((r.get("date", "") for r in rows), default=None)
    if not rows:
        warnings.append("no observations")
    return SourceStatus(path, True, source=source, as_of=as_of, kind=_classify_source(source, path), warnings=warnings).as_dict()


def rates_source_report(*, bond_csv: str, erp_json: str, fx_csv: str) -> dict:
    return {
        "bond_10y_5y_avg_source": inspect_bond_csv(bond_csv),
        "equity_risk_premium_source": inspect_erp_json(erp_json),
        "fx_eod_source": inspect_fx_csv(fx_csv),
        "note": "Real use requires versioned external exports (for example FRED/BNR for bonds, curated Damodaran-style ERP, provider EOD FX). Synthetic/template files are acceptable only for construction/testing.",
    }
