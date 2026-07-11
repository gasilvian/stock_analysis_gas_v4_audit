import gzip
import json
import zlib

import pytest

from sws_engine.sec.cik_resolver import load_cik_records, resolve_cik
from sws_engine.sec.companyfacts_adapter import fetch_companyfacts_live


class _Response:
    def __init__(self, body, content_encoding=None):
        self._body = body
        self.headers = {}
        if content_encoding:
            self.headers["Content-Encoding"] = content_encoding

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


@pytest.mark.parametrize(
    ("content_encoding", "encode"),
    [
        (None, lambda body: body),
        ("gzip", gzip.compress),
        ("deflate", zlib.compress),
        (
            "deflate",
            lambda body: zlib.compress(body)[2:-4],
        ),
    ],
    ids=["plain", "gzip", "zlib-deflate", "raw-deflate"],
)
def test_live_companyfacts_decodes_http_content_encoding(
    monkeypatch, content_encoding, encode
):
    expected = {"cik": 320193, "facts": {"us-gaap": {}}}
    body = encode(json.dumps(expected).encode("utf-8"))

    def _urlopen(request, timeout):
        assert request.get_header("Accept-encoding") == "gzip, deflate"
        assert timeout == 30
        return _Response(body, content_encoding)

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)
    assert fetch_companyfacts_live(
        320193,
        user_agent="offline-test automation@unit.test",
        sleep_seconds=0,
    ) == expected


@pytest.mark.parametrize(
    "raw",
    [
        {"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}},
        {"AAPL": {"cik": "0000320193", "exchange": "US"}},
        {"AAPL": "0000320193"},
        [{"ticker": "AAPL", "cik": "0000320193", "exchange": "US"}],
    ],
    ids=["official-sec", "simplified-object", "simplified-scalar", "list"],
)
def test_cik_map_declared_formats_resolve_and_normalize(tmp_path, raw):
    path = tmp_path / "cik-map.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    record = resolve_cik("aapl", path)

    assert record is not None
    assert record.ticker == "AAPL"
    assert record.cik10 == "0000320193"


def test_cik_map_missing_ticker_remains_unresolved(tmp_path):
    path = tmp_path / "cik-map.json"
    path.write_text(json.dumps({"AAPL": "320193"}), encoding="utf-8")

    assert resolve_cik("MSFT", path) is None
    assert load_cik_records(path)["AAPL"].cik == "0000320193"
