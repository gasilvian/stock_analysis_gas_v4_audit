"""HTTP error helpers for the API layer."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


def api_error(status_code: int, code: str, message: str, details: Any = None) -> HTTPException:
    body = {"error": code, "message": message}
    if details is not None:
        body["details"] = details
    return HTTPException(status_code=status_code, detail=body)


def bad_request(message: str, details: Any = None) -> HTTPException:
    return api_error(status.HTTP_400_BAD_REQUEST, "BAD_REQUEST", message, details)


def not_found(message: str, details: Any = None) -> HTTPException:
    return api_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message, details)


def unprocessable(message: str, details: Any = None) -> HTTPException:
    return api_error(422, "VALIDATION_ERROR", message, details)


def internal_error(message: str = "Internal API error") -> HTTPException:
    # Do not expose stack traces to clients.
    return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", message)
