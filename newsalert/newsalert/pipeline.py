"""Ingest raw items: dedupe -> stale/seed check -> store -> hand new items to the sink.

The sink is the AlertEngine (engine.py) in production; tests use a recorder.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

from .config import Settings, Source
from .db import Database
from .dedupe import is_stale, normalize_url, text_hash
from .models import RawItem
from .text import truncate

log = logging.getLogger("newsalert.pipeline")


class Sink(Protocol):
    async def on_new_item(self, item_id: int, item: RawItem, source: Source) -> None: ...


@dataclass
class IngestStats:
    new: int = 0
    duplicate: int = 0
    stale: int = 0
    seeded: int = 0


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

    async def retract(self, source: str, external_id: str, reason: str) -> bool:
        """A watcher saw an item disappear: post deleted, Wikipedia edit reverted, etc.

        Marks the item deleted and lets the sink send a "possibly false" follow-up.
        Returns True if the item was known.
        """
        row = self.db.conn.execute(
            "SELECT id, deleted_at FROM items WHERE source=? AND external_id=?", (source, external_id)
        ).fetchone()
        if row is None or row["deleted_at"] is not None:
            return False
        self.db.conn.execute("UPDATE items SET deleted_at=? WHERE id=?", (time.time(), row["id"]))
        self.db.audit("item.retracted", source=source, external_id=external_id, reason=reason)
        log.info("item.retracted", extra={"source": source, "item_id": row["id"], "reason": reason})
        handler = getattr(self.sink, "on_retraction", None)
        if handler is not None:
            try:
                await handler(row["id"], reason)
            except Exception:
                log.exception("sink.retraction_error", extra={"item_id": row["id"]})
        return True
