"""FastAPI dependencies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import Depends

from sws_engine.api.config import Settings, get_settings
from sws_engine.api.db_adapter import ApiDbAdapter


def get_db_adapter(settings: Settings = Depends(get_settings)) -> ApiDbAdapter:
    adapter = ApiDbAdapter(settings.db_path, settings.assumptions_path)
    try:
        yield adapter
    finally:
        adapter.close()


def load_fixture_payload(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
