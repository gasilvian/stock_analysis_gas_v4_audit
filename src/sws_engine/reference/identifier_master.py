"""Identifier Master builder and validator for v4.0 P0.4.

The builder is deliberately conservative: it can enrich a curated universe with
SEC CIK metadata, but it does not infer licensed identifiers such as CUSIP and
it does not guess ambiguous tickers.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sws_engine.sec.cik_resolver import load_cik_records

IDENTIFIER_MASTER_COLUMNS = [
    "ticker", "exchange", "country", "currency", "market", "industry", "sector",
    "company_type", "security_type", "primary_listing", "cik", "cik_source", "sic",
    "lei", "figi", "isin", "cusip", "is_adr", "is_foreign_issuer", "source_id",
    "source_tier", "source_quality", "source_class", "as_of", "review_status", "notes",
]


@dataclass
class IdentifierIssue:
    code: str
    message: str
    severity: str = "warning"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    with p.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _truthy(value: Any, default: str = "false") -> str:
    if value in (True, "true", "TRUE", "1", 1, "yes", "YES"):
        return "true"
    if value in (False, "false", "FALSE", "0", 0, "no", "NO"):
        return "false"
    return default


def _derive_security_type(row: dict[str, Any]) -> str:
    explicit = (row.get("security_type") or row.get("instrument_type") or "").strip().lower()
    if explicit:
        return explicit
    ticker = (row.get("ticker") or "").upper().strip()
    if ticker.endswith(".ETF") or "ETF" in (row.get("industry") or "").upper():
        return "etf"
    return "common"


def _derive_company_type(row: dict[str, Any], security_type: str) -> str:
    explicit = (row.get("company_type") or "").strip().lower()
    if explicit:
        return explicit
    if security_type in {"etf", "fund"}:
        return "fund_etf_excluded"
    industry = f"{row.get('industry', '')} {row.get('sector', '')}".lower()
    if "bank" in industry:
        return "bank"
    if "reit" in industry or "real estate investment" in industry:
        return "reit"
    if "insurance" in industry:
        return "insurance"
    return "standard_industrial"


def build_identifier_master(
    *,
    universe_csv: str | Path,
    output_csv: str | Path,
    cik_map: str | Path | None = None,
    as_of: str | None = None,
    review_status: str = "operator_review_required",
    source_id: str = "identifier_master_curated",
) -> dict[str, Any]:
    rows = _read_csv(universe_csv)
    cik_records = load_cik_records(cik_map) if cik_map else {}
    out_rows: list[dict[str, str]] = []
    issues: list[IdentifierIssue] = []
    seen: set[tuple[str, str]] = set()

    for idx, row in enumerate(rows, start=2):
        ticker = (row.get("ticker") or row.get("symbol") or "").upper().strip()
        if not ticker:
            issues.append(IdentifierIssue("IDENTIFIER_TICKER_MISSING", f"row {idx}: missing ticker", "error"))
            continue
        exchange = (row.get("exchange") or row.get("market") or "UNKNOWN").strip() or "UNKNOWN"
        key = (ticker, exchange.upper())
        if key in seen:
            issues.append(IdentifierIssue("IDENTIFIER_DUPLICATE_TICKER_EXCHANGE", f"duplicate ticker/exchange {ticker}/{exchange}", "error"))
            continue
        seen.add(key)
        cik = ""
        sic = ""
        cik_source = "UNKNOWN"
        rec = cik_records.get(ticker)
        if rec:
            cik = rec.cik10
            sic = rec.sic or ""
            cik_source = "sec_company_tickers"
        else:
            issues.append(IdentifierIssue("IDENTIFIER_CIK_UNKNOWN", f"{ticker}: CIK not found in CIK map", "warning"))
        security_type = _derive_security_type(row)
        company_type = _derive_company_type(row, security_type)
        is_foreign = _truthy(row.get("is_foreign_issuer"), "false")
        is_adr = _truthy(row.get("is_adr"), "true" if security_type == "adr" else "false")
        out_rows.append({
            "ticker": ticker,
            "exchange": exchange,
            "country": row.get("country", "") or "",
            "currency": row.get("currency", "") or "",
            "market": row.get("market", "") or "",
            "industry": row.get("industry", "") or "",
            "sector": row.get("sector", "") or "",
            "company_type": company_type,
            "security_type": security_type,
            "primary_listing": _truthy(row.get("primary_listing"), "true"),
            "cik": cik,
            "cik_source": cik_source,
            "sic": sic,
            "lei": row.get("lei", "") or "",
            "figi": row.get("figi", "") or "",
            "isin": row.get("isin", "") or "",
            "cusip": row.get("cusip", "") or "",
            "is_adr": is_adr,
            "is_foreign_issuer": is_foreign,
            "source_id": source_id,
            "source_tier": "curated",
            "source_quality": "exact_or_approximation" if not cik else "exact",
            "source_class": "E0" if cik else "E3",
            "as_of": as_of or "",
            "review_status": review_status,
            "notes": "CUSIP/ISIN/FIGI/LEI are optional/manual unless provided by a legitimate source. No licensed identifier was inferred.",
        })

    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=IDENTIFIER_MASTER_COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)

    status = "PASS_WITH_LIMITATIONS" if out_rows else "FAIL"
    if any(i.severity == "error" for i in issues):
        status = "FAIL"
    return {
        "status": status,
        "input_universe": str(universe_csv),
        "cik_map": str(cik_map) if cik_map else None,
        "output_csv": str(out_path),
        "rows_written": len(out_rows),
        "issues": [i.as_dict() for i in issues],
        "lineage": {
            "source_id": source_id,
            "source_tier": "curated",
            "source_quality": "exact_or_approximation",
            "source_class": "E0/E3",
            "review_status": review_status,
        },
    }


def validate_identifier_master(path: str | Path, *, require_reviewed: bool = False) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"status": "NOT_READY", "path": str(p), "rows": 0, "issues": [IdentifierIssue("IDENTIFIER_MASTER_MISSING", f"identifier master missing: {p}", "error").as_dict()]}
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    issues: list[IdentifierIssue] = []
    required = {"ticker", "exchange", "company_type", "security_type", "review_status"}
    missing = sorted(required - set(reader.fieldnames or []))
    if missing:
        issues.append(IdentifierIssue("IDENTIFIER_MASTER_MISSING_COLUMNS", f"missing columns: {missing}", "error"))
    seen: set[tuple[str, str]] = set()
    ciks = 0
    for idx, row in enumerate(rows, start=2):
        ticker = (row.get("ticker") or "").upper().strip()
        exchange = (row.get("exchange") or "").upper().strip()
        if not ticker:
            issues.append(IdentifierIssue("IDENTIFIER_MASTER_TICKER_MISSING", f"row {idx}: missing ticker", "error"))
        key = (ticker, exchange)
        if key in seen:
            issues.append(IdentifierIssue("IDENTIFIER_MASTER_DUPLICATE", f"duplicate {ticker}/{exchange}", "error"))
        seen.add(key)
        if row.get("cik"):
            ciks += 1
        if require_reviewed and row.get("review_status") not in {"reviewed", "operator_approved", "approved"}:
            issues.append(IdentifierIssue("IDENTIFIER_MASTER_REVIEW_REQUIRED", f"{ticker}: review_status not approved", "error"))
        if row.get("cusip") and row.get("source_id") == "identifier_master_curated":
            issues.append(IdentifierIssue("IDENTIFIER_MASTER_CUSIP_MANUAL_ONLY", f"{ticker}: CUSIP present; verify legitimate source", "warning"))
    status = "PASS" if rows and not any(i.severity == "error" for i in issues) else "NOT_READY"
    return {
        "status": status,
        "path": str(p),
        "rows": len(rows),
        "rows_with_cik": ciks,
        "issues": [i.as_dict() for i in issues],
    }


def write_json_report(report: dict[str, Any], output: str | Path | None) -> None:
    if output is None:
        return
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
