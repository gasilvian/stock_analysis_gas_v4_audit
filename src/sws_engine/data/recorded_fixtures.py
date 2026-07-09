"""Recorded live-provider fixtures.

Normal tests must remain offline. These helpers load/save yfinance-shaped raw
snapshots that tests and demos can use without network access.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def save_recorded_snapshot(ticker: str, snapshot: Dict[str, Any], path: str | os.PathLike) -> str:
    path = Path(path)
    if path.is_dir() or str(path).endswith(os.sep):
        path = path / f"{ticker.upper()}_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, sort_keys=True)
    return str(path)


def load_recorded_snapshot(ticker: str, path: str | os.PathLike = "data/recorded_yfinance") -> Dict[str, Any]:
    path = Path(path)
    if path.is_dir():
        path = path / f"{ticker.upper()}_snapshot.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
