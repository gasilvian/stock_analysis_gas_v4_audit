"""FastAPI application for the SWS Snowflake Engine v3.1 backend layer."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sws_engine.api.config import get_settings
from sws_engine.api.routes_company import router as company_router
from sws_engine.api.routes_meta import public_router as public_meta_router
from sws_engine.api.routes_meta import router as meta_router
from sws_engine.api.routes_portfolio import router as portfolio_router
from sws_engine.api.routes_query import router as query_router
from sws_engine.api.routes_live import router as live_router
from sws_engine.api.routes_ops import router as ops_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SWS Snowflake Engine v3.1 API",
        version=settings.api_version,
        description=(
            "Internal backend API for the SWS Snowflake Engine v3.1 release "
            "candidate. Uses synthetic/no-network data in this build; not "
            "investment advice and not the live Simply Wall St model."
        ),
        openapi_tags=[
            {"name": "company", "description": "Company analysis endpoints"},
            {"name": "portfolio", "description": "Portfolio analysis endpoints"},
            {"name": "query", "description": "History, checks and screener endpoints"},
            {"name": "governance", "description": "Assumptions and lineage governance"},
            {"name": "meta", "description": "Service metadata and health"},
        ],
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(public_meta_router)
    app.include_router(meta_router)
    app.include_router(company_router)
    app.include_router(portfolio_router)
    app.include_router(query_router)
    app.include_router(live_router)
    app.include_router(ops_router)
    return app


app = create_app()
