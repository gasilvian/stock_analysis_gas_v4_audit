"""Query/governance API routes: screener, averages, assumptions."""
from __future__ import annotations

import hashlib
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query

from sws_engine.api.config import Settings, get_settings
from sws_engine.api.db_adapter import AXES, ApiDbAdapter
from sws_engine.api.deps import get_db_adapter
from sws_engine.api.errors import bad_request, not_found
from sws_engine.api.schemas import ScreenerResponse
from sws_engine.api.security import require_api_key

router = APIRouter(tags=["query", "governance"], dependencies=[Depends(require_api_key)])


@router.get("/screener", response_model=ScreenerResponse)
def screener(
    axis: str | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=0, le=6),
    min_coverage: float = Query(default=0.66, ge=0.0, le=1.0),
    provider_profile: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    if axis is not None and axis not in AXES:
        raise bad_request(f"axis must be one of {AXES}")
    rows = db.screener(
        axis=axis,
        min_score=0 if min_score is None else min_score,
        min_coverage=min_coverage,
        provider_profile=provider_profile,
        limit=limit,
    )
    return {"rows": rows}


@router.get("/averages/{market}/{date}")
def averages_snapshot(
    market: str,
    date: str,
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    snapshot = db.get_averages_snapshot(market, date)
    if not snapshot:
        raise not_found(f"No averages snapshot found for market '{market}' and date '{date}'.")
    return snapshot


@router.get("/assumptions/current")
def assumptions_current(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    try:
        with open(settings.assumptions_path, "rb") as fh:
            raw_bytes = fh.read()
    except FileNotFoundError:
        raise not_found(f"Assumptions file not found at '{settings.assumptions_path}'.")
    raw = yaml.safe_load(raw_bytes.decode("utf-8")) or {}
    return {
        "assumptions_path": settings.assumptions_path,
        "assumptions_hash": hashlib.sha256(raw_bytes).hexdigest(),
        "metadata": raw.get("metadata", {}),
        "unknown_scoring_policy": raw.get("unknown_scoring_policy", {}),
        "provider_profiles": raw.get("provider_profiles", {}),
        "raw": raw,
    }
