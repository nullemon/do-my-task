from __future__ import annotations

import time
from email.utils import formatdate
from xml.sax.saxutils import escape

import httpx
import pytest

from newsalert.config import Settings, Source
from newsalert.db import Database
from newsalert.pipeline import Pipeline


class RecordingSink:
    def __init__(self) -> None:
        self.items = []

    async def on_new_item(self, item_id, item, source) -> None:
        self.items.append((item_id, item))


def make_rss(entries: list[dict]) -> bytes:
    """entries: dicts with title, link, guid?, summary?, age_s? (seconds before now) or pub=None."""
    now = time.time()
    parts = []
    for e in entries:
        pub = ""
        if e.get("age_s") is not None:
            pub = f"<pubDate>{formatdate(now - e['age_s'], usegmt=True)}</pubDate>"
        guid = f"<guid>{escape(e['guid'])}</guid>" if e.get("guid") else ""
        parts.append(
            f"<item><title>{escape(e['title'])}</title><link>{escape(e['link'])}</link>"
            f"{guid}<description>{escape(e.get('summary', ''))}</description>{pub}</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        "<title>Test Feed</title><link>https://example.com</link><description>t</description>"
        + "".join(parts)
        + "</channel></rss>"
    ).encode()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


@pytest.fixture
def sink() -> RecordingSink:
    return RecordingSink()


@pytest.fixture
def pipeline(db, settings, sink) -> Pipeline:
    return Pipeline(db, settings, sink)


def make_source(name="Test Feed", trust="major", category="anime", url="https://example.com/feed", **kw) -> Source:
    return Source(name=name, type="rss", url=url, category=category, trust=trust, **kw)


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))
