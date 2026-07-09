"""Portfolio API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

import sws_engine
from sws_engine.api.config import Settings, get_settings
from sws_engine.api.db_adapter import ApiDbAdapter
from sws_engine.api.deps import get_db_adapter
from sws_engine.api.errors import internal_error, not_found, unprocessable
from sws_engine.api.schemas import ApiRunMetadata, ApiWrappedResponse, PortfolioAnalyzeRequest
from sws_engine.api.security import require_api_key
from sws_engine.config.assumptions_loader import load_assumptions
from sws_engine.portfolio.portfolio_run import run_portfolio_analysis

router = APIRouter(tags=["portfolio"], dependencies=[Depends(require_api_key)])


@router.post("/analyze/portfolio", response_model=ApiWrappedResponse)
def analyze_portfolio(
    request: PortfolioAnalyzeRequest,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    try:
        output = run_portfolio_analysis(request.input_payload, load_assumptions(settings.assumptions_path))
    except KeyError as exc:
        raise unprocessable("Invalid portfolio payload; required field is missing.", {"field": str(exc)})
    except ValueError as exc:
        raise unprocessable("Invalid portfolio payload.", {"error": str(exc)})
    except Exception as exc:
        raise internal_error(f"Portfolio analysis failed: {exc.__class__.__name__}")
    ids = db.save_portfolio_output(output, request.input_payload) if request.persist else {}
    return ApiWrappedResponse(
        metadata=ApiRunMetadata(
            run_id=ids.get("run_id"),
            portfolio_id=ids.get("portfolio_id"),
            persisted=bool(request.persist),
            engine_version=sws_engine.__version__,
            api_version=settings.api_version,
            data_layer=settings.data_layer,
        ),
        output=output,
    )


@router.get("/portfolios/{portfolio_id}/latest", response_model=ApiWrappedResponse)
def latest_portfolio(
    portfolio_id: str,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    rec = db.get_latest_portfolio(portfolio_id)
    if not rec:
        raise not_found(f"No portfolio run found for portfolio_id '{portfolio_id}'.")
    return ApiWrappedResponse(
        metadata=ApiRunMetadata(
            run_id=rec["run_id"],
            portfolio_id=portfolio_id,
            persisted=True,
            engine_version=sws_engine.__version__,
            api_version=settings.api_version,
            data_layer=settings.data_layer,
        ),
        output=rec["output"],
    )


@router.get("/portfolios/{portfolio_id}/history")
def portfolio_history(
    portfolio_id: str,
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    points = db.get_portfolio_history(portfolio_id)
    if not points:
        raise not_found(f"No portfolio history found for portfolio_id '{portfolio_id}'.")
    return {"portfolio_id": portfolio_id, "points": points}
