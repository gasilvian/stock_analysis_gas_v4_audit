"""Pydantic wrappers for the API. Engine outputs stay as raw dictionaries."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CompanyAnalyzeRequest(BaseModel):
    input_payload: Dict[str, Any]
    persist: bool = False
    snapshot: bool = False


class PortfolioAnalyzeRequest(BaseModel):
    input_payload: Dict[str, Any]
    persist: bool = False


class ApiRunMetadata(BaseModel):
    run_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    persisted: bool = False
    engine_version: str
    api_version: str = "0.1.0"
    data_layer: str = "synthetic/no-network"


class ApiWrappedResponse(BaseModel):
    metadata: ApiRunMetadata
    output: Dict[str, Any]


class HistoryPoint(BaseModel):
    valuation_date: str
    score_raw: int
    known_checks_count: Optional[int] = None
    unknown_checks_count: Optional[int] = None
    coverage_pct: float
    provider_profile: Optional[str] = None
    run_id: Optional[str] = None
    axis: Optional[str] = None


class HistoryResponse(BaseModel):
    ticker: str
    axis: Optional[str] = None
    points: List[HistoryPoint]


class ChecksQueryResponse(BaseModel):
    ticker: str
    latest_only: bool = True
    checks: List[Dict[str, Any]]


class ScreenerResponse(BaseModel):
    rows: List[Dict[str, Any]]


class MetaHealthResponse(BaseModel):
    status: str = "ok"
    engine_version: str
    api_version: str = "0.1.0"
    db_path: str
    data_layer: str = "synthetic/no-network"
    output_schema_path: str
    assumptions_path: str
    last_batch_run: Optional[str] = None
    validation_status: str = "PASS WITH LIMITATIONS"
    tests_recorded: str = "118 passed, 2 skipped"
    live_market_data: bool = False
    dashboard_available: bool = False
    yfinance_live_provider_available: bool = False


class RootResponse(BaseModel):
    name: str = "SWS Snowflake Engine v3.1 API"
    status: str = "ok"
    docs: str = "/docs"
    health: str = "/meta/health"


class YFinanceBuildPayloadRequest(BaseModel):
    ticker: str
    valuation_date: Optional[str] = None
    market: Optional[str] = None
    industry: Optional[str] = None
    refresh: bool = False
    overrides: Dict[str, Any] = Field(default_factory=dict)


class YFinanceBuildPayloadResponse(BaseModel):
    metadata: Dict[str, Any]
    input_payload: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    capability_summary: Dict[str, Any] = Field(default_factory=dict)


class YFinanceLiveAnalyzeRequest(BaseModel):
    ticker: str
    valuation_date: Optional[str] = None
    market: Optional[str] = None
    industry: Optional[str] = None
    refresh: bool = False
    persist: bool = True
    overrides: Dict[str, Any] = Field(default_factory=dict)
