"""CIK resolver for SEC `company_tickers.json`.

The resolver accepts the SEC public JSON shape (dict keyed by integers with
`ticker`, `cik_str`, `title`) and a simpler list/dict fixture shape. It never
infers a CIK. If a ticker is absent, callers must return UNKNOWN/skipped rather
than guessing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class CikRecord:
    ticker: str
    cik: str
    title: str | None = None
    exchange: str | None = None
    sic: str | None = None

    @property
    def cik10(self) -> str:
        return normalize_cik(self.cik)


def normalize_cik(value: str | int) -> str:
    text = str(value).strip()
    if text.upper().startswith("CIK"):
        text = text[3:]
    text = "".join(ch for ch in text if ch.isdigit())
    if not text:
        raise ValueError("CIK value has no digits")
    return text.zfill(10)


def _iter_records(raw: Any) -> Iterable[dict[str, Any]]:
    if isinstance(raw, dict):
        # SEC shape: {"0": {"cik_str": 320193, "ticker": "AAPL", ...}}
        if raw and all(
            isinstance(v, dict)
            and bool(v.get("ticker") or v.get("symbol"))
            and v.get("cik_str") not in (None, "")
            for v in raw.values()
        ):
            yield from raw.values()
            return
        # Simplified shape: {"AAPL": {"cik": "0000320193", ...}}
        for ticker, value in raw.items():
            if isinstance(value, dict):
                rec = dict(value)
                rec.setdefault("ticker", ticker)
                yield rec
            elif isinstance(value, (str, int)):
                yield {"ticker": ticker, "cik": value}
        return
    if isinstance(raw, list):
        yield from (r for r in raw if isinstance(r, dict))


def load_cik_records(path: str | Path) -> dict[str, CikRecord]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CIK map not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    records: dict[str, CikRecord] = {}
    for rec in _iter_records(raw):
        ticker = str(rec.get("ticker") or rec.get("symbol") or "").upper().strip()
        cik_value = rec.get("cik") or rec.get("cik_str") or rec.get("CIK")
        if not ticker or cik_value in (None, ""):
            continue
        records[ticker] = CikRecord(
            ticker=ticker,
            cik=normalize_cik(cik_value),
            title=rec.get("title") or rec.get("name"),
            exchange=rec.get("exchange"),
            sic=str(rec.get("sic")) if rec.get("sic") not in (None, "") else None,
        )
    return records


def resolve_cik(ticker: str, cik_map_path: str | Path) -> CikRecord | None:
    records = load_cik_records(cik_map_path)
    return records.get(str(ticker).upper().strip())
