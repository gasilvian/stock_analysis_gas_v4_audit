"""Curated rates / ERP workflow for v4.0 P0.4.

This module deliberately avoids mandatory live internet dependencies. Operators
can feed official exports (for example a FRED CSV download) into a versioned
curated file. The output remains review-aware and lineage-rich; missing or draft
review state never becomes a silent production-ready assumption.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


DATE_COLUMNS = ("DATE", "date", "observation_date")
VALUE_COLUMNS = ("DGS10", "value", "yield_10y", "rate")


@dataclass
class ValidationMessage:
    code: str
    message: str
    severity: str = "warning"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_decimal_rate(raw: str | float | int | None) -> float | None:
    """Normalize a rate to decimal form.

    FRED DGS10 CSVs are percentage points (e.g. 4.25). The engine's bond CSV
    uses decimals (e.g. 0.0425). Values already in decimal form are preserved.
    Missing observations such as '.' are skipped.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text == ".":
        return None
    value = float(text)
    if abs(value) > 1:
        value = value / 100.0
    return value


def _get_first(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def build_curated_bond_csv_from_export(
    *,
    input_csv: str | Path,
    output_csv: str | Path,
    country: str = "US",
    currency: str = "USD",
    tenor: str = "10Y",
    series_id: str = "DGS10",
    source: str = "FRED_DGS10_EXPORT",
    source_url_reference: str | None = None,
    source_as_of: str | None = None,
    review_status: str = "operator_review_required",
    notes: str | None = None,
) -> dict[str, Any]:
    """Convert a local official export into the engine's curated bond CSV.

    The function accepts both FRED-style CSVs (DATE,DGS10) and the existing
    engine shape (country,date,yield_10y). It does not invent missing rates.
    """
    in_path = Path(input_csv)
    if not in_path.exists():
        raise FileNotFoundError(f"rates input CSV not found: {in_path}")
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    observations: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    with in_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, start=2):
            row_country = (row.get("country") or country).strip()
            if row_country.upper() != country.upper():
                continue
            raw_date = _get_first(row, DATE_COLUMNS)
            raw_rate = _get_first(row, VALUE_COLUMNS)
            obs_date = _parse_iso_date(str(raw_date) if raw_date is not None else None)
            try:
                rate = _normalize_decimal_rate(raw_rate)
            except (TypeError, ValueError):
                skipped_rows.append({"row": idx, "reason_code": "INVALID_RATE_VALUE", "raw_rate": raw_rate})
                continue
            if obs_date is None or rate is None:
                skipped_rows.append({"row": idx, "reason_code": "MISSING_DATE_OR_RATE"})
                continue
            observations.append({
                "country": country,
                "date": obs_date.isoformat(),
                "yield_10y": f"{rate:.8f}",
                "currency": currency,
                "tenor": tenor,
                "source": source,
                "source_id": series_id,
                "source_tier": "curated",
                "source_quality": "exact",
                "source_class": "E0",
                "source_as_of": source_as_of or obs_date.isoformat(),
                "review_status": review_status,
                "source_url_reference": source_url_reference or "local_operator_export",
                "notes": notes or "Converted from local official/exported rates CSV. Operator review required unless explicitly marked reviewed.",
            })

    observations.sort(key=lambda r: r["date"])
    fieldnames = [
        "country", "date", "yield_10y", "currency", "tenor", "source", "source_id",
        "source_tier", "source_quality", "source_class", "source_as_of", "review_status",
        "source_url_reference", "notes",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(observations)

    report = {
        "status": "PASS_WITH_LIMITATIONS" if observations else "FAIL",
        "input_csv": str(in_path),
        "output_csv": str(out_path),
        "country": country,
        "currency": currency,
        "tenor": tenor,
        "series_id": series_id,
        "source": source,
        "review_status": review_status,
        "observations_written": len(observations),
        "skipped_rows": skipped_rows,
        "first_date": observations[0]["date"] if observations else None,
        "last_date": observations[-1]["date"] if observations else None,
        "lineage": {
            "source_quality": "exact",
            "source_class": "E0",
            "source_tier": "curated",
            "operator_review_required": review_status != "reviewed",
        },
    }
    return report


def validate_bond_curated_csv(path: str | Path, *, require_reviewed: bool = False) -> dict[str, Any]:
    p = Path(path)
    messages: list[ValidationMessage] = []
    if not p.exists():
        return {
            "status": "NOT_READY",
            "path": str(p),
            "observations": 0,
            "messages": [ValidationMessage("BOND_CSV_MISSING", f"bond CSV missing: {p}", "error").as_dict()],
        }
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    required = {"country", "date", "yield_10y", "source", "review_status"}
    missing = sorted(required - set(reader.fieldnames or []))
    if missing:
        messages.append(ValidationMessage("BOND_CSV_MISSING_COLUMNS", f"missing columns: {missing}", "error"))
    reviewed_count = 0
    for idx, row in enumerate(rows, start=2):
        if _parse_iso_date(row.get("date")) is None:
            messages.append(ValidationMessage("BOND_CSV_INVALID_DATE", f"invalid date at row {idx}", "error"))
        try:
            rate = float(row.get("yield_10y", ""))
            if not (-0.10 <= rate <= 0.50):
                messages.append(ValidationMessage("BOND_CSV_RATE_OUT_OF_RANGE", f"yield_10y out of range at row {idx}", "warning"))
        except ValueError:
            messages.append(ValidationMessage("BOND_CSV_INVALID_RATE", f"invalid yield_10y at row {idx}", "error"))
        if row.get("review_status") == "reviewed":
            reviewed_count += 1
    if require_reviewed and rows and reviewed_count != len(rows):
        messages.append(ValidationMessage("BOND_CSV_REVIEW_REQUIRED", "not all rows have review_status=reviewed", "error"))
    status = "PASS" if rows and not any(m.severity == "error" for m in messages) else "NOT_READY"
    return {
        "status": status,
        "path": str(p),
        "observations": len(rows),
        "reviewed_observations": reviewed_count,
        "first_date": min((r.get("date", "") for r in rows), default=None),
        "last_date": max((r.get("date", "") for r in rows), default=None),
        "messages": [m.as_dict() for m in messages],
    }


def _status_from_review(review_status: str | None, expires_at: str | None) -> tuple[str, list[ValidationMessage]]:
    messages: list[ValidationMessage] = []
    status = (review_status or "").strip().lower()
    if status not in {"reviewed", "operator_approved", "approved"}:
        messages.append(ValidationMessage("ERP_REVIEW_REQUIRED", "ERP review_status must be reviewed/operator_approved/approved", "error"))
    expiry = _parse_iso_date(expires_at)
    today = date.today()
    if expiry is None:
        messages.append(ValidationMessage("ERP_EXPIRY_REQUIRED", "ERP expires_at is required", "error"))
    elif expiry < today:
        messages.append(ValidationMessage("ERP_REVIEW_EXPIRED", f"ERP expired on {expiry.isoformat()}", "error"))
    return status, messages


def validate_erp_curated_json(
    path: str | Path,
    *,
    require_reviewed: bool = False,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Validate curated ERP JSON and its review lifecycle."""
    p = Path(path)
    if not p.exists():
        return {
            "status": "NOT_READY",
            "path": str(p),
            "messages": [ValidationMessage("ERP_JSON_MISSING", f"ERP JSON missing: {p}", "error").as_dict()],
        }
    data = json.loads(p.read_text(encoding="utf-8"))
    messages: list[ValidationMessage] = []
    countries = data.get("countries") or {}
    if not isinstance(countries, dict) or not countries:
        messages.append(ValidationMessage("ERP_COUNTRIES_EMPTY", "countries table missing/empty", "error"))
    source = data.get("source") or data.get("source_id")
    if not source:
        messages.append(ValidationMessage("ERP_SOURCE_REQUIRED", "source/source_id is required", "error"))
    review_status = data.get("review_status") or data.get("review")
    expires_at = data.get("expires_at")
    _, lifecycle_messages = _status_from_review(review_status, expires_at)
    if require_reviewed:
        messages.extend(lifecycle_messages)
    else:
        messages.extend(m if m.code == "ERP_REVIEW_EXPIRED" else ValidationMessage(m.code, m.message, "warning") for m in lifecycle_messages)

    for country, entry in countries.items():
        if not isinstance(entry, dict):
            messages.append(ValidationMessage("ERP_COUNTRY_ENTRY_INVALID", f"{country}: entry must be object", "error"))
            continue
        value = entry.get("erp", entry.get("equity_risk_premium"))
        try:
            erp_value = float(value)
            if not (0 <= erp_value <= 0.50):
                messages.append(ValidationMessage("ERP_VALUE_OUT_OF_RANGE", f"{country}: ERP out of range", "warning"))
        except (TypeError, ValueError):
            messages.append(ValidationMessage("ERP_VALUE_INVALID", f"{country}: ERP value missing/invalid", "error"))
        country_review = entry.get("review_status")
        if country_review and country_review not in {"reviewed", "operator_approved", "approved"}:
            messages.append(ValidationMessage("ERP_COUNTRY_REVIEW_REQUIRED", f"{country}: country review_status not approved", "error" if require_reviewed else "warning"))

    status = "PASS" if not any(m.severity == "error" for m in messages) else "NOT_READY"
    return {
        "status": status,
        "path": str(p),
        "source": source,
        "as_of": data.get("as_of") or as_of,
        "review_status": review_status,
        "expires_at": expires_at,
        "countries_count": len(countries) if isinstance(countries, dict) else 0,
        "lineage": {
            "source_quality": "assumption",
            "source_class": "E2",
            "source_tier": "manual",
            "sensitivity_required": bool(data.get("sensitivity_required", True)),
        },
        "messages": [m.as_dict() for m in messages],
    }


def write_json_report(report: dict[str, Any], output: str | Path | None) -> None:
    if output is None:
        return
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
