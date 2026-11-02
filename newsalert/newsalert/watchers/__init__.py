"""Watchers: cheap, AI-free pollers/streams that turn sources into RawItems.

`build_watchers` returns objects with `.name` and `async run()`; main.py starts one
task per object. Polling sources (rss, youtube) get one watcher each. Streams and
schedulers serve many sources from one object: one Jetstream connection for all
Bluesky accounts, one scheduler for all X accounts, one EventStreams connection
for Wikipedia.
"""

from __future__ import annotations

import logging

from ..config import Source
from .base import PollingWatcher, StreamWatcher, Watcher, WatcherContext
from .bluesky import BlueskyWatcher
from .rss import RssWatcher
from .wikipedia import WikipediaWatcher
from .x_api import XWatcher
from .youtube import YouTubeWatcher
from .youtube import interval_for as youtube_interval

log = logging.getLogger("newsalert.watchers")

__all__ = [
    "BlueskyWatcher",
    "PollingWatcher",
    "RssWatcher",
    "StreamWatcher",
    "Watcher",
    "WatcherContext",
    "WikipediaWatcher",
    "XWatcher",
    "YouTubeWatcher",
    "build_watchers",
]


def build_watchers(sources: list[Source], ctx: WatcherContext) -> list[Watcher]:
    polling = ctx.settings.polling
    enabled = [s for s in sources if s.enabled]
    watchers: list[Watcher] = []

    pollers: list[tuple[Source, type[PollingWatcher], int]] = []
    for s in enabled:
        if s.type == "rss":
            pollers.append((s, RssWatcher, s.effective_interval(polling)))
        elif s.type == "youtube":
            pollers.append((s, YouTubeWatcher, youtube_interval(s, ctx.settings)))
    n = max(len(pollers), 1)
    for idx, (source, cls, interval) in enumerate(pollers):
        # Spread first polls evenly so we don't hit everything at once.
        start_delay = (idx / n) * min(polling.startup_stagger, interval)
        try:
            watchers.append(cls(source, ctx, interval=interval, start_delay=start_delay))
        except ValueError as exc:  # e.g. a YouTube handle where a channel id is needed
            log.error("watcher.bad_source", extra={"source": source.name, "error": str(exc)})

    bluesky = [s for s in enabled if s.type == "bluesky"]
    if bluesky:
        watchers.append(BlueskyWatcher(bluesky, ctx))

    x_sources = [s for s in enabled if s.type == "x"]
    if x_sources:
        watchers.append(XWatcher(x_sources, ctx))

    wiki = [s for s in enabled if s.type == "wikipedia"]
    if wiki:
        if wiki[0].trust != "signal":
            log.warning("wikipedia.trust_forced", extra={"source": wiki[0].name, "configured": wiki[0].trust})
        watchers.append(WikipediaWatcher(wiki[0], ctx))
        for extra in wiki[1:]:
            log.warning("watcher.duplicate_stream", extra={"source": extra.name, "type": "wikipedia", "using": wiki[0].name})
    return watchers
