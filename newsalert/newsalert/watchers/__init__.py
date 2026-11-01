"""Watchers: cheap, AI-free pollers/streams that turn sources into RawItems."""

from __future__ import annotations

import logging

from ..config import Source
from .base import PollingWatcher, WatcherContext
from .rss import RssWatcher

log = logging.getLogger("newsalert.watchers")

# Watcher types land build step by step; unknown types are skipped with a log line.
_WATCHERS: dict[str, type[PollingWatcher]] = {
    "rss": RssWatcher,
}
_PLANNED = {"youtube": 5, "bluesky": 5, "x": 6, "wikipedia": 7}


def build_watchers(sources: list[Source], ctx: WatcherContext) -> list[PollingWatcher]:
    polling = ctx.settings.polling
    active = [s for s in sources if s.enabled and s.type in _WATCHERS]
    for s in sources:
        if s.enabled and s.type not in _WATCHERS:
            log.warning(
                "watcher.not_implemented",
                extra={"source": s.name, "type": s.type, "build_step": _PLANNED.get(s.type)},
            )
    watchers = []
    n = max(len(active), 1)
    for idx, source in enumerate(active):
        interval = source.effective_interval(polling)
        # Spread first polls evenly so we don't hit everything at once.
        start_delay = (idx / n) * min(polling.startup_stagger, interval)
        watchers.append(_WATCHERS[source.type](source, ctx, interval=interval, start_delay=start_delay))
    return watchers
