import copy
import json
import os

import pytest
from fastapi.testclient import TestClient

from sws_engine.api.app import app

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SWS_DB_PATH", str(tmp_path / "api_sws.db"))
    monkeypatch.setenv("SWS_ASSUMPTIONS_PATH", os.path.join(ROOT, "config", "assumptions.yaml"))
    monkeypatch.setenv("SWS_SCHEMA_PATH", os.path.join(ROOT, "schemas", "output_schema.json"))
    monkeypatch.setenv("SWS_API_AUTH_ENABLED", "false")
    return TestClient(app)


@pytest.fixture
def api_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("SWS_DB_PATH", str(tmp_path / "api_sws.db"))
    monkeypatch.setenv("SWS_ASSUMPTIONS_PATH", os.path.join(ROOT, "config", "assumptions.yaml"))
    monkeypatch.setenv("SWS_SCHEMA_PATH", os.path.join(ROOT, "schemas", "output_schema.json"))
    return {
        "db": str(tmp_path / "api_sws.db"),
        "assumptions": os.path.join(ROOT, "config", "assumptions.yaml"),
        "schema": os.path.join(ROOT, "schemas", "output_schema.json"),
    }


@pytest.fixture
def demo_company_payload():
    with open(os.path.join(ROOT, "tests", "fixtures", "demo_complete_non_financial.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def demo_portfolio_payload():
    with open(os.path.join(ROOT, "tests", "fixtures", "demo_portfolio.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def yfinance_degraded_payload(demo_company_payload):
    p = copy.deepcopy(demo_company_payload)
    p["ticker"] = "DEGRADED"
    p["provider_profile"] = "yfinance_pragmatic"
    for f in ("roe_3y_estimate", "estimated_payout_3y", "intangible_assets", "market_averages", "industry_averages"):
        p.pop(f, None)
    return p
