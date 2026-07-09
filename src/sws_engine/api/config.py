"""FastAPI settings for the SWS Snowflake Engine API.

The API layer is intentionally thin: it exposes the existing engine and
persistence layer without changing the v3.1 output contract.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


DEFAULT_CORS = "http://localhost:8501,http://127.0.0.1:8501"


def _as_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    db_path: str = "data/sws.db"
    assumptions_path: str = "config/assumptions.yaml"
    schema_path: str = "schemas/output_schema.json"
    audit_policies_path: str = "config/audit_policies.yaml"
    source_registry_path: str = "config/source_registry.yaml"
    identifier_master_path: str = "data/real_sources/reference/identifier_master.csv"
    sensitivity_config_path: str = "config/sensitivity.yaml"
    reason_code_dictionary_path: str = "config/reason_code_dictionary.yaml"
    api_key: Optional[str] = None
    api_auth_enabled: bool = False
    cors_origins: tuple[str, ...] = ("http://localhost:8501", "http://127.0.0.1:8501")
    api_version: str = "0.1.0"
    data_layer: str = "synthetic/no-network"
    live_market_data_enabled: bool = False


def get_settings() -> Settings:
    """Read settings from environment on every call.

    No lru_cache is used so tests can change environment variables without
    process restarts.
    """
    return Settings(
        db_path=os.getenv("SWS_DB_PATH", "data/sws.db"),
        assumptions_path=os.getenv("SWS_ASSUMPTIONS_PATH", "config/assumptions.yaml"),
        schema_path=os.getenv("SWS_SCHEMA_PATH", "schemas/output_schema.json"),
        audit_policies_path=os.getenv("SWS_AUDIT_POLICIES_PATH", "config/audit_policies.yaml"),
        source_registry_path=os.getenv("SWS_SOURCE_REGISTRY_PATH", "config/source_registry.yaml"),
        identifier_master_path=os.getenv("SWS_IDENTIFIER_MASTER_PATH", "data/real_sources/reference/identifier_master.csv"),
        sensitivity_config_path=os.getenv("SWS_SENSITIVITY_CONFIG_PATH", "config/sensitivity.yaml"),
        reason_code_dictionary_path=os.getenv("SWS_REASON_CODE_DICTIONARY_PATH", "config/reason_code_dictionary.yaml"),
        api_key=os.getenv("SWS_API_KEY") or None,
        api_auth_enabled=_as_bool(os.getenv("SWS_API_AUTH_ENABLED"), False),
        cors_origins=tuple(_split_csv(os.getenv("SWS_CORS_ORIGINS", DEFAULT_CORS))),
        live_market_data_enabled=_as_bool(os.getenv("SWS_LIVE_MARKET_DATA_ENABLED"), False),
    )
