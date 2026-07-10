"""Runtime TTL/staleness enforcement for curated-source injections (P2.3-enf).

Gap identified by the Post-P1.6 follow-up audit: static validators check
``expires_at`` and the registry declares ``ttl_days`` per source, but nothing
compared a curated observation's age against its TTL at the moment of
injection — a stale bond yield or FX rate flowed into payloads silently
(the curated FX file was already past its 7-day TTL at approval time, noted
only in a file comment).

Doctrine: staleness is DEGRADATION, and degradation must be visible. The
enforcement here therefore:
- computes the observation age against the registry ``ttl_days`` for the
  source id;
- when stale, emits a ``CURATED_SOURCE_STALE`` warning and stamps the
  injected field's lineage with ``stale: true`` + ``stale_age_days`` — the
  value is still injected (an old official observation beats an invented
  one), but nobody can miss that it is old;
- when a source carries an explicit ``expires_at`` and it has passed
  (ERP), injection is REFUSED — expiry is a curation contract, stronger
  than a TTL heuristic, mirroring the estimates-pack behavior.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY_PATH = "config/source_registry.yaml"


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value)[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def ttl_days_for_source(source_id: str,
                        registry_path: str | Path = DEFAULT_REGISTRY_PATH) -> int | None:
    try:
        registry = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return None
    for entry in registry.get("sources") or []:
        if entry.get("id") == source_id:
            ttl = entry.get("ttl_days")
            return int(ttl) if ttl is not None else None
    return None


def staleness_check(
    as_of: Any,
    *,
    source_id: str,
    valuation_date: Any,
    ttl_days: int | None = None,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    """Return {"stale", "age_days", "ttl_days", "warning"}.

    Unknown as_of or missing TTL yields stale=False with a null age — the
    check never invents staleness it cannot demonstrate; absence of a TTL in
    the registry means the operator has not declared a freshness contract.
    """
    ttl = ttl_days if ttl_days is not None else ttl_days_for_source(source_id, registry_path)
    observed = _parse_date(as_of)
    today = _parse_date(valuation_date) or date.today()
    if observed is None or ttl is None:
        return {"stale": False, "age_days": None, "ttl_days": ttl, "warning": None}
    age = (today - observed).days
    if age <= ttl:
        return {"stale": False, "age_days": age, "ttl_days": ttl, "warning": None}
    warning = (f"CURATED_SOURCE_STALE: {source_id} observation as_of {observed.isoformat()} is "
               f"{age} days old, exceeding ttl_days={ttl}; value injected with visible "
               "staleness — refresh the curated source")
    return {"stale": True, "age_days": age, "ttl_days": ttl, "warning": warning}


def mark_lineage_stale(lineage_entry: dict[str, Any], check: dict[str, Any]) -> None:
    """Stamp an injected field's lineage with the staleness verdict in place."""
    if check.get("stale"):
        lineage_entry["stale"] = True
        lineage_entry["stale_age_days"] = check.get("age_days")
        lineage_entry["stale_ttl_days"] = check.get("ttl_days")
