"""Ingest raw items: dedupe -> stale/seed check -> store -> hand new items to the sink.

Step 1 sink prints to the console. Later steps swap in triage + alerting.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from .config import Settings, Source
from .db import Database
from .dedupe import is_stale, normalize_url, text_hash
from .models import RawItem
from .text import humanize_age, truncate

log = logging.getLogger("newsalert.pipeline")


class Sink(Protocol):
    async def on_new_item(self, item_id: int, item: RawItem, source: Source) -> None: ...


@dataclass
class IngestStats:
    new: int = 0
    duplicate: int = 0
    stale: int = 0
    seeded: int = 0


class ConsoleSink:
    """Prints each new item. Used by build step 1."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock

    async def on_new_item(self, item_id: int, item: RawItem, source: Source) -> None:
        age = None if item.published_at is None else self.clock() - item.published_at
        print(
            f"\n[{item.category.upper()}] [{item.trust}] {item.source} · {humanize_age(age)}\n"
            f"  {truncate(item.title, 200)}\n"
            f"  {item.url or '(no url)'}",
            flush=True,
        )


class Pipeline:
    def __init__(self, db: Database, settings: Settings, sink: Sink) -> None:
        self.db = db
        self.settings = settings
        self.sink = sink

    async def ingest(self, source: Source, items: list[RawItem], *, seeding: bool) -> IngestStats:
        """Store new items. When `seeding`, store them as already-seen without alerting."""
        stats = IngestStats()
        p = self.settings.pipeline
        # Oldest first so output and story order follow publication order.
        ordered = sorted(items, key=lambda i: i.published_at or i.fetched_at)
        for item in ordered:
            url_norm = normalize_url(item.url)
            thash = text_hash(item.text)
            dup = self.db.find_duplicate(
                source=item.source,
                external_id=item.external_id,
                url_norm=url_norm,
                text_hash=thash,
                text_since=item.fetched_at - p.text_dedupe_hours * 3600,
            )
            if dup:
                stats.duplicate += 1
                continue

            if seeding:
                status = "seeded"
            elif is_stale(item.published_at, item.fetched_at, p.stale_minutes):
                status = "stale"
            else:
                status = "new"

            item_id = self.db.insert_item(item, url_norm=url_norm, text_hash=thash, status=status)
            if item_id is None:  # lost a race with a unique index
                stats.duplicate += 1
                continue

            setattr(stats, status, getattr(stats, status) + 1)
            if status == "stale":
                log.info(
                    "item.stale",
                    extra={
                        "source": item.source,
                        "age_s": round(item.fetched_at - (item.published_at or item.fetched_at)),
                        "title": truncate(item.title, 120),
                    },
                )
            elif status == "new":
                log.info("item.new", extra={"source": item.source, "item_id": item_id, "url": item.url})
                try:
                    await self.sink.on_new_item(item_id, item, source)
                except Exception:
                    log.exception("sink.error", extra={"source": item.source, "item_id": item_id})

        if seeding:
            self.db.audit("source.seeded", source=source.name, items=stats.seeded)
            log.info("source.seeded", extra={"source": source.name, "items": stats.seeded})
        return stats
