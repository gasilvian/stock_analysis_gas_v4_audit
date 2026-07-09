"""Minimal API-key security for internal use."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from sws_engine.api.config import Settings, get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    supplied_key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.api_auth_enabled:
        return None
    if not settings.api_key or supplied_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Valid X-API-Key header is required.",
            },
        )
    return None
