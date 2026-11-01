"""RSS/Atom watcher using conditional GET (ETag / If-Modified-Since)."""

from __future__ import annotations

import calendar
import time
from typing import Any

import feedparser
import httpx

from ..config import Source
from ..models import RawItem
from ..text import strip_html, truncate
from .base import PollingWatcher, PollResult, RateLimited, SourceError, parse_retry_after

_MAX_TEXT = 1500


async def fetch_feed(
    client: httpx.AsyncClient, source: Source, state: dict[str, Any] | None = None
) -> PollResult:
    state = state or {}
    headers = {}
    if state.get("etag"):
        headers["If-None-Match"] = state["etag"]
    if state.get("last_modified"):
        headers["If-Modified-Since"] = state["last_modified"]

    resp = await client.get(source.url, headers=headers)
    if resp.status_code == 304:
        return PollResult(items=[])
    if resp.status_code in (429, 503) or (resp.status_code == 403 and "retry-after" in resp.headers):
        raise RateLimited(parse_retry_after(resp.headers.get("retry-after")), f"HTTP {resp.status_code}")
    resp.raise_for_status()

    fetched_at = time.time()
    items = parse_feed(resp.content, source, fetched_at, content_type=resp.headers.get("content-type", ""))
    return PollResult(
        items=items,
        state={"etag": resp.headers.get("etag"), "last_modified": resp.headers.get("last-modified")},
    )


def parse_feed(content: bytes, source: Source, fetched_at: float, content_type: str = "") -> list[RawItem]:
    parsed = feedparser.parse(content, response_headers={"content-type": content_type} if content_type else None)
    if parsed.bozo and not parsed.entries:
        raise SourceError(f"unparseable feed: {parsed.get('bozo_exception')!r}")
    if not parsed.version and not parsed.entries:
        raise SourceError("response is not an RSS/Atom feed (got HTML or an error page?)")
    items = []
    for entry in parsed.entries:
        item = _entry_to_item(entry, source, fetched_at)
        if item is not None:
            items.append(item)
    return items


def _entry_to_item(entry: Any, source: Source, fetched_at: float) -> RawItem | None:
    title = strip_html(entry.get("title"))
    body = strip_html(entry.get("summary") or _first_content(entry))
    if body.startswith(title):  # many feeds repeat the headline in the summary
        body = body[len(title):].strip()
    if not title and not body:
        return None
    if not title:
        title = truncate(body, 140)
    link = entry.get("link") or None
    return RawItem.from_source(
        source,
        url=link,
        account=entry.get("author") or None,
        external_id=entry.get("id") or link,
        title=title,
        text=truncate(f"{title}\n{body}".strip(), _MAX_TEXT),
        published_at=_entry_time(entry),
        fetched_at=fetched_at,
    )


def _first_content(entry: Any) -> str:
    content = entry.get("content") or []
    return content[0].get("value", "") if content else ""


def _entry_time(entry: Any) -> float | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(key)
        if st:
            return float(calendar.timegm(st))  # feedparser normalizes to UTC
    return None


class RssWatcher(PollingWatcher):
    async def poll(self, state: dict[str, Any]) -> PollResult:
        return await fetch_feed(self.ctx.client, self.source, state)
