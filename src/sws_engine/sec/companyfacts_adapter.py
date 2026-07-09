"""SEC CompanyFacts adapter.

Network access is optional and never required in CI. Offline mode reads
previously recorded CompanyFacts files from a fixture/cache directory.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from sws_engine.sec.cik_resolver import normalize_cik

SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
DEFAULT_USER_AGENT = "sws-snowflake-engine/4.0 internal-personal-educational contact@example.invalid"


def companyfacts_filename(cik: str | int) -> str:
    return f"CIK{normalize_cik(cik)}.json"


def load_companyfacts_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CompanyFacts file not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def find_companyfacts_file(cik: str | int, *dirs: str | Path | None) -> Path | None:
    name = companyfacts_filename(cik)
    for d in dirs:
        if not d:
            continue
        p = Path(d) / name
        if p.exists():
            return p
    return None


def fetch_companyfacts_live(
    cik: str | int,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    sleep_seconds: float = 0.12,
) -> dict[str, Any]:
    """Fetch CompanyFacts using stdlib urllib.

    This function is intentionally not used by offline tests. The sleep keeps
    callers below the SEC fair-access limit when used in small personal batches.
    """
    time.sleep(max(0.0, sleep_seconds))
    url = SEC_COMPANYFACTS_URL.format(cik=normalize_cik(cik))
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec - public SEC API URL
        return json.loads(resp.read().decode("utf-8"))


def get_companyfacts(
    cik: str | int,
    *,
    cache_dir: str | Path | None = None,
    fixture_dir: str | Path | None = None,
    live: bool = False,
    refresh: bool = False,
    user_agent: str = DEFAULT_USER_AGENT,
) -> tuple[dict[str, Any], str]:
    """Return (CompanyFacts JSON, source_path_or_url).

    If `live` is false, the function only reads fixture/cache. Missing data is a
    FileNotFoundError so the CLI can mark ticker as skipped/UNKNOWN instead of
    inventing data.
    """
    cache_path = Path(cache_dir) / companyfacts_filename(cik) if cache_dir else None
    if not refresh:
        existing = find_companyfacts_file(cik, fixture_dir, cache_dir)
        if existing:
            return load_companyfacts_file(existing), str(existing)
    if not live:
        raise FileNotFoundError(f"No cached CompanyFacts file for CIK{normalize_cik(cik)} and live mode is disabled")
    facts = fetch_companyfacts_live(cik, user_agent=user_agent)
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(facts, indent=2, sort_keys=True), encoding="utf-8")
        return facts, str(cache_path)
    return facts, SEC_COMPANYFACTS_URL.format(cik=normalize_cik(cik))
