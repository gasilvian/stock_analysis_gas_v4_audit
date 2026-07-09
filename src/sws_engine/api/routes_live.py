"""Optional live-provider endpoints for yfinance_pragmatic."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import sws_engine
from sws_engine.api.config import Settings, get_settings
from sws_engine.api.db_adapter import ApiDbAdapter
from sws_engine.api.deps import get_db_adapter
from sws_engine.api.schemas import ApiRunMetadata, ApiWrappedResponse, YFinanceBuildPayloadRequest, YFinanceBuildPayloadResponse, YFinanceLiveAnalyzeRequest
from sws_engine.api.security import require_api_key
from sws_engine.orchestration.company_run import run_company_analysis
from sws_engine.providers.live_errors import YFinanceDependencyError, LiveProviderError
from sws_engine.providers.yfinance_mapper import capability_summary_from_payload

router = APIRouter(tags=["company"], dependencies=[Depends(require_api_key)])


def _provider(refresh: bool = False):
    from sws_engine.providers.yfinance_live import YFinanceLiveProvider
    return YFinanceLiveProvider(refresh=refresh)


@router.post("/providers/yfinance/build-payload", response_model=YFinanceBuildPayloadResponse)
def build_payload_yfinance(request: YFinanceBuildPayloadRequest):
    try:
        provider = _provider(refresh=request.refresh)
        payload = provider.build_payload(
            request.ticker,
            valuation_date=request.valuation_date,
            market=request.market,
            industry=request.industry,
            overrides=request.overrides,
        )
    except YFinanceDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except LiveProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    warnings = payload.get("builder_warnings", []) or []
    summary = capability_summary_from_payload(payload)
    degradation_count = summary.get("counts", {}).get("missing", 0) + summary.get("counts", {}).get("approximation", 0)
    return {
        "metadata": {
            "provider": "yfinance",
            "provider_profile": "yfinance_pragmatic",
            "live_market_data": True,
            "degradation_count": degradation_count,
        },
        "input_payload": payload,
        "warnings": warnings,
        "capability_summary": summary,
    }


@router.post("/analyze/company-live", response_model=ApiWrappedResponse)
def analyze_company_live(
    request: YFinanceLiveAnalyzeRequest,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    try:
        provider = _provider(refresh=request.refresh)
        payload = provider.build_payload(
            request.ticker,
            valuation_date=request.valuation_date,
            market=request.market,
            industry=request.industry,
            overrides=request.overrides,
        )
        output = run_company_analysis(payload, settings.assumptions_path, settings.schema_path)
    except YFinanceDependencyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except LiveProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"company-live failed: {exc.__class__.__name__}")
    run_id = db.save_company_output(output, payload) if request.persist else None
    return ApiWrappedResponse(
        metadata=ApiRunMetadata(
            run_id=run_id,
            persisted=bool(request.persist),
            engine_version=sws_engine.__version__,
            api_version=settings.api_version,
            data_layer="live/yfinance_pragmatic",
        ),
        output=output,
    )
