"""SEC CompanyFacts adapter.

Network access is optional and never required in CI. Offline mode reads
previously recorded CompanyFacts files from a fixture/cache directory.
"""
from __future__ import annotations

import gzip
import json
import os
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Any

from sws_engine.sec.cik_resolver import normalize_cik

SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_USER_AGENT_ENV = "SWS_SEC_USER_AGENT"
# P1.3a: the former silent default. Kept only so validation can explicitly
# reject it if it leaks in from old configs; it is never used as a fallback.
PLACEHOLDER_USER_AGENT = "sws-snowflake-engine/4.0 internal-personal-educational contact@example.invalid"


def resolve_user_agent(explicit: str | None = None) -> str:
    """Resolve and validate the SEC User-Agent for live fetches.

    SEC fair-access policy requires a declared User-Agent identifying the
    requester with a real contact (conventionally "name/app contact@email").
    Resolution order: explicit argument, then the SWS_SEC_USER_AGENT
    environment variable. There is NO built-in fallback: a live fetch with a
    missing or placeholder UA raises ValueError with remediation guidance
    instead of silently violating the policy. Offline/cache reads never need
    a UA and never call this function.
    """
    candidate = (explicit or os.environ.get(SEC_USER_AGENT_ENV) or "").strip()
    if not candidate:
        raise ValueError(
            "SEC live fetch requires a real User-Agent per SEC fair-access policy. "
            f"Pass --user-agent 'your-name your-app contact@your-domain' or set {SEC_USER_AGENT_ENV}."
        )
    lowered = candidate.lower()
    if lowered == PLACEHOLDER_USER_AGENT.lower() or "example.invalid" in lowered:
        raise ValueError(
            "SEC live fetch rejected: the User-Agent is the repository placeholder. "
            f"Provide a real contact via --user-agent or {SEC_USER_AGENT_ENV}."
        )
    if "@" not in candidate or "." not in candidate.split("@")[-1]:
        raise ValueError(
            "SEC live fetch rejected: User-Agent must include a real contact email "
            "(SEC fair-access policy), e.g. 'jane-doe research-engine jane@domain.com'."
        )
    return candidate


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
    user_agent: str | None = None,
    sleep_seconds: float = 0.12,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Fetch CompanyFacts using stdlib urllib.

    P1.3a hardening: the User-Agent is resolved and validated BEFORE any
    network activity (no placeholder fallback), and transient SEC responses
    (429/5xx) are retried with exponential backoff (1s, 2s, 4s). The
    pre-request sleep keeps callers below the SEC fair-access limit when
    used in small personal batches. Not used by offline tests.
    """
    resolved_agent = resolve_user_agent(user_agent)
    url = SEC_COMPANYFACTS_URL.format(cik=normalize_cik(cik))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": resolved_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    attempt = 0
    while True:
        time.sleep(max(0.0, sleep_seconds))
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec - public SEC API URL
                body = resp.read()
                content_encoding = (
                    resp.headers.get("Content-Encoding") or ""
                ).lower()

                if "gzip" in content_encoding:
                    body = gzip.decompress(body)
                elif "deflate" in content_encoding:
                    try:
                        body = zlib.decompress(body)
                    except zlib.error:
                        body = zlib.decompress(body, -zlib.MAX_WBITS)

                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(2 ** attempt)
                attempt += 1
                continue
            raise


def get_companyfacts(
    cik: str | int,
    *,
    cache_dir: str | Path | None = None,
    fixture_dir: str | Path | None = None,
    live: bool = False,
    refresh: bool = False,
    user_agent: str | None = None,
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
