"""P1.3a tests: SEC live-fetch User-Agent hardening.

The Post-P0.14 audit flagged that live SEC fetches silently used a
placeholder User-Agent (contact@example.invalid), violating the SEC
fair-access policy requirement for an identifiable contact. These tests pin
the hardened behavior: no fallback, placeholder rejected, env var honored,
validation happens BEFORE any network activity, and offline/cache reads
never require a UA.
"""
import json

import pytest

from sws_engine.sec.companyfacts_adapter import (
    PLACEHOLDER_USER_AGENT,
    SEC_USER_AGENT_ENV,
    fetch_companyfacts_live,
    get_companyfacts,
    resolve_user_agent,
)


def test_resolve_user_agent_accepts_real_contact():
    ua = resolve_user_agent("jane-doe research-engine jane@domain.com")
    assert "jane@domain.com" in ua


def test_resolve_user_agent_rejects_missing(monkeypatch):
    monkeypatch.delenv(SEC_USER_AGENT_ENV, raising=False)
    with pytest.raises(ValueError, match="fair-access"):
        resolve_user_agent(None)


def test_resolve_user_agent_rejects_placeholder(monkeypatch):
    monkeypatch.delenv(SEC_USER_AGENT_ENV, raising=False)
    with pytest.raises(ValueError, match="placeholder"):
        resolve_user_agent(PLACEHOLDER_USER_AGENT)
    with pytest.raises(ValueError, match="placeholder"):
        resolve_user_agent("anything contact@example.invalid")


def test_resolve_user_agent_rejects_contactless():
    with pytest.raises(ValueError, match="contact email"):
        resolve_user_agent("just-an-app-name-no-email")


def test_resolve_user_agent_reads_env(monkeypatch):
    monkeypatch.setenv(SEC_USER_AGENT_ENV, "ops sws-engine ops@real-domain.org")
    assert resolve_user_agent(None) == "ops sws-engine ops@real-domain.org"


def test_live_fetch_validates_ua_before_any_network(monkeypatch):
    monkeypatch.delenv(SEC_USER_AGENT_ENV, raising=False)

    def _no_network(*_a, **_k):  # pragma: no cover - must never run
        raise AssertionError("network was attempted before UA validation")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", _no_network)
    with pytest.raises(ValueError, match="fair-access"):
        fetch_companyfacts_live(320193)


def test_offline_cache_read_requires_no_user_agent(tmp_path, monkeypatch):
    monkeypatch.delenv(SEC_USER_AGENT_ENV, raising=False)
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "CIK0000320193.json").write_text(json.dumps({"cik": 320193, "facts": {}}), encoding="utf-8")
    facts, source = get_companyfacts(320193, cache_dir=cache, live=False)
    assert facts["cik"] == 320193
    assert source.endswith("CIK0000320193.json")
