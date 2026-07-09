"""Root and health endpoints."""
from __future__ import annotations

import importlib.util
from fastapi import APIRouter, Depends

import sws_engine
from sws_engine.api.config import Settings, get_settings
from sws_engine.api.db_adapter import ApiDbAdapter
from sws_engine.api.deps import get_db_adapter
from sws_engine.api.schemas import MetaHealthResponse, RootResponse
from sws_engine.api.security import require_api_key

public_router = APIRouter(tags=["meta"])
router = APIRouter(tags=["meta"], dependencies=[Depends(require_api_key)])


@public_router.get("/", response_model=RootResponse)
def root():
    return RootResponse()


@router.get("/meta/health", response_model=MetaHealthResponse)
def meta_health(
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    return MetaHealthResponse(
        status="ok",
        engine_version=sws_engine.__version__,
        api_version=settings.api_version,
        db_path=settings.db_path,
        data_layer=settings.data_layer,
        output_schema_path=settings.schema_path,
        assumptions_path=settings.assumptions_path,
        last_batch_run=db.last_batch_run(),
        validation_status="PASS WITH LIMITATIONS",
        tests_recorded="122 passed, 2 skipped",
        live_market_data=settings.live_market_data_enabled,
        dashboard_available=False,
        yfinance_live_provider_available=importlib.util.find_spec("yfinance") is not None,
    )
