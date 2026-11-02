"""YouTube channel watcher: the public per-channel Atom feed, no API key.

`https://www.youtube.com/feeds/videos.xml?channel_id=UC...` lists a channel's ~15
newest uploads. It is fetched with the same conditional-GET path as RSS sources.
A source gives either `account: UC...` (the channel id, put into
`youtube.feed_url_template`) or a full feed `url`.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import Settings, Source
from .base import PollingWatcher, PollResult
from .rss import fetch_feed

_CHANNEL_ID = re.compile(r"^UC[0-9A-Za-z_-]{22}$")


def is_channel_id(value: str | None) -> bool:
    return bool(value and _CHANNEL_ID.match(value.strip()))


def feed_url(source: Source, settings: Settings) -> str:
    if source.url:
        return source.url
    channel_id = (source.account or "").strip()
    if not is_channel_id(channel_id):
        raise ValueError(
            f"source {source.name!r}: account {channel_id!r} is not a YouTube channel id "
            "(UC + 22 characters; handles like @name don't work with the feed)"
        )
    return settings.youtube.feed_url_template.format(channel_id=channel_id)


def feed_source(source: Source, settings: Settings) -> Source:
    """The source with its feed URL filled in, so the RSS fetch/parse path can serve it."""
    return source.model_copy(update={"url": feed_url(source, settings)})


def interval_for(source: Source, settings: Settings) -> int:
    return max(source.interval or settings.youtube.interval, settings.polling.min_interval)


class YouTubeWatcher(PollingWatcher):
    def __init__(self, source: Source, ctx, *, interval: float, start_delay: float = 0.0) -> None:
        super().__init__(source, ctx, interval=interval, start_delay=start_delay)
        # Fail at startup (in build_watchers) rather than on every poll.
        self._feed_source = feed_source(source, ctx.settings)

    async def poll(self, state: dict[str, Any]) -> PollResult:
        return await fetch_feed(self.ctx.client, self._feed_source, state)
