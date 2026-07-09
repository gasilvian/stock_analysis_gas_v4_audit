"""Helpers for field-level provider lineage.

The v3.1 output schema requires run-level lineage. The live provider keeps
field-level lineage inside the input payload so checks/reports can trace how a
payload was constructed without changing output_schema.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def field_meta(*, provider: str, source_field: str | None = None,
               source_quality: str = "missing", source_class: str = "E3",
               as_of: str | None = None, transform: str | None = None,
               reason_code: str | None = None) -> Dict[str, Any]:
    return {
        "provider": provider,
        "source_field": source_field,
        "source_quality": source_quality,
        "source_class": source_class,
        "as_of": as_of,
        "transform": transform,
        "reason_code": reason_code,
    }


def attach_field_lineage(payload: dict, field: str, meta: Dict[str, Any]) -> None:
    lineage = payload.setdefault("lineage", {})
    lineage.setdefault("field_lineage", {})[field] = meta
