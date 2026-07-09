"""Dashboard configuration read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DashboardSettings:
    api_url: str = "http://127.0.0.1:8000"
    api_key: Optional[str] = None
    timeout_seconds: float = 30.0


def get_dashboard_settings() -> DashboardSettings:
    timeout_raw = os.getenv("DASHBOARD_TIMEOUT_SECONDS", "30")
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 30.0
    return DashboardSettings(
        api_url=os.getenv("DASHBOARD_API_URL", "http://127.0.0.1:8000").rstrip("/"),
        api_key=os.getenv("DASHBOARD_API_KEY") or None,
        timeout_seconds=timeout,
    )
