"""Minimal Identifier Master reader for Model Applicability P0.2.

Identifier Master is optional in P0.2. Missing files degrade to UNKNOWN/manual
review rather than fabricating classification data.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable

DEFAULT_IDENTIFIER_MASTER_PATH = "data/real_sources/reference/identifier_master.csv"


def load_identifier_master(path: str | Path = DEFAULT_IDENTIFIER_MASTER_PATH) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def find_identifier_record(
    ticker: str | None,
    exchange: str | None = None,
    *,
    records: Iterable[Dict[str, Any]] | None = None,
    path: str | Path = DEFAULT_IDENTIFIER_MASTER_PATH,
) -> Dict[str, Any] | None:
    if not ticker:
        return None
    rows = list(records) if records is not None else load_identifier_master(path)
    t = str(ticker).upper()
    ex = str(exchange or "").upper()
    matches = [row for row in rows if str(row.get("ticker", "")).upper() == t]
    if ex:
        scoped = [row for row in matches if str(row.get("exchange", "")).upper() == ex]
        if scoped:
            return dict(scoped[0])
    return dict(matches[0]) if matches else None
