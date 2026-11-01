import time
from pathlib import Path

import httpx
import pytest

from newsalert.watchers.base import RateLimited, SourceError, parse_retry_after
from newsalert.watchers.rss import fetch_feed, parse_feed

from conftest import make_rss, make_source, mock_client

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_rss_fixture():
    src = make_source()
    items = parse_feed((FIXTURES / "sample_rss.xml").read_bytes(), src, fetched_at=time.time())
    assert len(items) == 3
    first = items[0]
    assert first.title == "Studio X Announces Season 2 of Y"
    assert "<p>" not in first.text and "&amp;" not in first.text
    assert "Cast & staff return" in first.text
    assert first.external_id == "ann-123"
    assert first.published_at == 1793440800.0  # Sat, 31 Oct 2026 10:00:00 GMT
    assert first.source == src.name and first.trust == "major" and first.category == "anime"
    # entry without a date
    assert items[2].published_at is None


def test_parse_atom_fixture():
    items = parse_feed((FIXTURES / "sample_atom.xml").read_bytes(), make_source(), fetched_at=time.time())
    assert len(items) == 1
    assert items[0].url == "https://www.youtube.com/watch?v=abc123"
    assert items[0].external_id == "yt:video:abc123"
    assert items[0].published_at is not None


def test_parse_garbage_raises():
    with pytest.raises(SourceError):
        parse_feed(b"<html><body>Access denied</body></html>", make_source(), fetched_at=time.time())


async def test_conditional_get_uses_etag_and_handles_304():
    seen_headers = []
    body = make_rss([{"title": "Hello world news item", "link": "https://e.com/1", "age_s": 60}])

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, content=body, headers={"ETag": '"v1"', "Last-Modified": "Sat, 31 Oct 2026 10:00:00 GMT"})

    src = make_source()
    async with mock_client(handler) as client:
        first = await fetch_feed(client, src, {})
        assert len(first.items) == 1
        assert first.state == {"etag": '"v1"', "last_modified": "Sat, 31 Oct 2026 10:00:00 GMT"}
        second = await fetch_feed(client, src, first.state)
    assert second.items == [] and second.state == {}
    assert seen_headers[1]["if-none-match"] == '"v1"'
    assert seen_headers[1]["if-modified-since"] == "Sat, 31 Oct 2026 10:00:00 GMT"


async def test_429_raises_rate_limited_with_retry_after():
    async with mock_client(lambda r: httpx.Response(429, headers={"Retry-After": "120"})) as client:
        with pytest.raises(RateLimited) as info:
            await fetch_feed(client, make_source(), {})
    assert info.value.retry_after == 120


async def test_http_error_raises():
    async with mock_client(lambda r: httpx.Response(500)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_feed(client, make_source(), {})


def test_parse_retry_after_http_date():
    now = 1_793_440_800.0  # Sat, 31 Oct 2026 10:00:00 GMT
    assert parse_retry_after("Sat, 31 Oct 2026 10:02:00 GMT", now=now) == 120
    assert parse_retry_after("garbage", now=now) is None
    assert parse_retry_after(None) is None
