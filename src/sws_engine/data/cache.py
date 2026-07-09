"""Disk cache with TTL for synthetic artifacts and optional live providers."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

DEFAULT_TTLS = {"price": 1, "fx": 1, "financials": 7, "averages": 1, "full_snapshot": 1}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class DiskCache:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = key.replace("/", "_").replace(":", "_")
        return os.path.join(self.root, f"{safe}.json")

    def get(self, key: str, ttl_days: float = None):
        p = self._path(key)
        if not os.path.exists(p):
            return None
        if ttl_days is not None:
            age_days = (time.time() - os.path.getmtime(p)) / 86400
            if age_days > ttl_days:
                return None
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def put(self, key: str, value):
        with open(self._path(key), "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2)
        return value


class JsonDiskCache(DiskCache):
    """Metadata-aware JSON cache used by live providers."""

    def __init__(self, root: str = "data/cache/yfinance"):
        super().__init__(root)

    def get_with_metadata(self, key: str, ttl_days: float | None = None) -> Dict[str, Any] | None:
        p = Path(self._path(key))
        if not p.exists():
            return None
        with p.open("r", encoding="utf-8") as fh:
            cached = json.load(fh)
        if ttl_days is not None:
            age_days = (time.time() - p.stat().st_mtime) / 86400
            if age_days > ttl_days:
                cached.setdefault("cache", {})["stale"] = True
                return None
        cached.setdefault("cache", {})["stale"] = False
        return cached

    def put_with_metadata(self, key: str, value: Dict[str, Any], *, ttl_days: float | None = None,
                          provider: str = "yfinance", provider_version: str | None = None) -> Dict[str, Any]:
        wrapped = dict(value)
        wrapped["cache"] = {
            "cached_at": _utc_now(),
            "provider": provider,
            "provider_version": provider_version,
            "ttl_days": ttl_days,
            "stale": False,
        }
        self.put(key, wrapped)
        return wrapped
