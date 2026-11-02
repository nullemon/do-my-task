"""Story engine: new item -> cluster -> triage -> confidence -> alert / follow-up.

Speed first: the first ring goes out as soon as triage passes. Later sources
only update the story (possibly sending a quiet "now confirmed" follow-up);
they never ring again.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable

from .alert import Alert
from .alert.format import retraction_alert, story_alert, upgrade_alert
from .confidence import RANK, SourceRef, label_for
from .config import AppConfig, Source
from .db import Database
from .dedupe import ItemFeatures, StoryFeatures, item_features, match_story
from .models import RawItem
from .triage import TriageInput, TriageResult, Triager
from .watchlist import WatchlistIndex, subject_key

log = logging.getLogger("newsalert.engine")


class AlertEngine:
    """Pipeline sink. Set `.dispatcher` before items arrive."""

    def __init__(
        self,
        db: Database,
        cfg: AppConfig,
        triager: Triager,
        index: WatchlistIndex,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.db = db
        self.cfg = cfg
        self.settings = cfg.settings
        self.triager = triager
        self.index = index
        self.clock = clock
        self.dispatcher = None  # alert.dispatch.Dispatcher
        self._lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(self.settings.triage.max_concurrency)
        self._tasks: set[asyncio.Task] = set()
        self._token_cache: dict[int, set[str]] = {}  # item id -> content tokens

    # ------------------------------------------------------------------ sink API

    async def on_new_item(self, item_id: int, item: RawItem, source: Source) -> None:
        task = asyncio.create_task(self._process_safe(item_id, item), name=f"item:{item_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def on_retraction(self, item_id: int, reason: str) -> None:
        await self._retract(item_id, reason)

    async def drain(self) -> None:
        """Wait for all in-flight items (tests, replay)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    # ------------------------------------------------------------------ processing

    async def _process_safe(self, item_id: int, item: RawItem) -> None:
        try:
            await self._process(item_id, item)
        except Exception:
            log.exception("engine.item_failed", extra={"item_id": item_id, "source": item.source})

    async def _process(self, item_id: int, item: RawItem) -> None:
        feats = item_features(item.title, item.text, self.index)
        async with self._sem:
            # 1. Cheap clustering against open stories.
            async with self._lock:
                decision = match_story(
                    feats, self._open_story_features(), title_similarity=self.settings.cluster.title_similarity,
                    subject_in_text=self._subject_in(item),
                )
                if decision.story_id is not None:
                    await self._join(decision.story_id, item_id, item, why=decision.reason)
                    return

            # 2. Ambiguous (same entity, unclear event): ask Haiku to break the tie.
            if decision.ambiguous and self.settings.cluster.ai_tiebreak:
                for story_id in decision.ambiguous[:2]:
                    story = self.db.get_story(story_id)
                    if story is None:
                        continue
                    other = f"{story['headline']}\n{story['summary'] or ''}"
                    if await self.triager.same_event(f"{item.title}\n{item.text[:500]}", other):
                        async with self._lock:
                            await self._join(story_id, item_id, item, why="ai tie-break")
                        return

            # 3. Triage (outside the lock so other items keep flowing).
            result = await self.triager.triage(TriageInput(
                source=item.source, trust=item.trust, category=item.category, title=item.title,
                text=item.text, watchlist_names=sorted(feats.entities),
            ))
            triaged_at = self.clock()

            # 4. Re-check under the lock: a parallel item may have opened the story meanwhile.
            async with self._lock:
                decision = match_story(
                    feats, self._open_story_features(), title_similarity=self.settings.cluster.title_similarity,
                    subject_in_text=self._subject_in(item),
                )
                existing = decision.story_id or self._find_by_subject(result)
                if existing is not None:
                    await self._join(existing, item_id, item, why=decision.reason if decision.story_id else "same subject+event")
                    return
                story_id = self._create_story(item_id, item, feats, result, triaged_at)

        await self._decide(story_id)

    # ------------------------------------------------------------------ clustering helpers

    def _window_start(self) -> float:
        return self.clock() - self.settings.cluster.window_hours * 3600

    def _open_story_features(self) -> list[StoryFeatures]:
        out = []
        for s in self.db.stories_since(self._window_start()):
            items = self.db.story_items(s["id"])
            out.append(StoryFeatures(
                story_id=s["id"],
                subject_key=s["subject_key"] or "",
                event_type=s["event_type"],
                entities=set(json.loads(s["entities"] or "[]")),
                tokens=[self._tokens_for(i) for i in items[:8]],
            ))
        if len(self._token_cache) > 5000:
            self._token_cache.clear()
        return out

    def _tokens_for(self, item_row) -> set[str]:
        tokens = self._token_cache.get(item_row["id"])
        if tokens is None:
            tokens = item_features(item_row["title"], "", self.index).tokens
            self._token_cache[item_row["id"]] = tokens
        return tokens

    def _subject_in(self, item: RawItem):
        text_key = subject_key(f"{item.title} {item.text[:300]}")

        def check(key: str) -> bool:
            return len(key) >= 6 and key in text_key

        return check

    def _find_by_subject(self, result: TriageResult) -> int | None:
        key = self.index.canonical(result.subject)
        if not key:
            return None
        for s in self.db.stories_since(self._window_start()):
            if s["subject_key"] == key and s["event_type"] == result.event_type:
                return s["id"]
        return None

    # ------------------------------------------------------------------ story lifecycle

    def _label(self, story_id: int) -> str:
        items = self.db.story_items(story_id, include_deleted=False)
        return label_for(SourceRef(i["source"], i["trust"], i["source_group"]) for i in items)

    def _create_story(self, item_id: int, item: RawItem, feats: ItemFeatures, r: TriageResult, triaged_at: float) -> int:
        entry = self.index.lookup(r.subject)
        entities = set(feats.entities) | ({entry.name} if entry else set())
        on_watchlist = r.ai_ok and (entry is not None or self._subject_matches_entities(r.subject, feats))
        importance = min(5, r.importance + (self.settings.triage.watchlist_boost if on_watchlist else 0))
        story_id = self.db.create_story(
            category=r.category, event_type=r.event_type, subject=r.subject,
            subject_key=self.index.canonical(r.subject), importance=importance, is_rumor=int(r.is_rumor),
            summary=r.summary, relevant=int(r.relevant), ai_ok=int(r.ai_ok), headline=item.title,
            entities=json.dumps(sorted(entities), ensure_ascii=False), watchlist=int(on_watchlist),
            first_item_id=item_id, published_at=item.published_at, fetched_at=item.fetched_at,
            triaged_at=triaged_at, status="new",
        )
        self.db.set_item_story(item_id, story_id)
        self.db.update_story(story_id, confidence=self._label(story_id))
        log.info("story.created", extra={
            "story_id": story_id, "subject": r.subject, "event": r.event_type, "importance": importance,
            "relevant": r.relevant, "ai_ok": r.ai_ok, "watchlist": on_watchlist, "ai_error": r.error,
        })
        return story_id

    def _subject_matches_entities(self, subject: str, feats: ItemFeatures) -> bool:
        if feats.risky_only:
            return False
        key = subject_key(subject)
        return any(subject_key(e) in key or key in subject_key(e) for e in feats.entities if len(subject_key(e)) >= 4)

    async def _decide(self, story_id: int) -> None:
        story = self.db.get_story(story_id)
        threshold = self.settings.triage.importance_threshold
        if not story["relevant"] or (story["importance"] or 0) < threshold:
            self.db.update_story(story_id, status="dropped")
            log.info("story.dropped", extra={
                "story_id": story_id, "relevant": bool(story["relevant"]), "importance": story["importance"],
            })
            return
        importance = story["importance"] or 0
        urgent = (
            story["event_type"] == "death"
            or importance >= 5
            or (story["watchlist"] and importance >= 4)
        )
        urgency = "urgent" if urgent else "normal"
        self.db.update_story(story_id, urgency=urgency)
        await self.dispatcher.ring_story(story_id, urgency)

    def build_ring_alert(self, story_id: int, urgency: str, muted: bool) -> Alert | None:
        story = self.db.get_story(story_id)
        items = self.db.story_items(story_id, include_deleted=False)
        if story is None or not items:
            return None
        return story_alert(
            story, items, urgency=urgency, max_links=self.settings.alerts.max_extra_links,
            now=self.clock(), muted=muted,
        )

    async def _join(self, story_id: int, item_id: int, item: RawItem, *, why: str) -> None:
        self.db.set_item_story(item_id, story_id)
        story = self.db.get_story(story_id)
        new_label = self._label(story_id)
        self.db.update_story(story_id, confidence=new_label)
        log.info("story.joined", extra={
            "story_id": story_id, "item_id": item_id, "source": item.source, "why": why, "label": new_label,
        })
        told = story["told_rank"]
        if story["status"] == "alerted" and told is not None and RANK[new_label] > told:
            items = self.db.story_items(story_id, include_deleted=False)
            fresh = self.db.get_story(story_id)
            confirming = [i["source"] for i in items if i["trust"] in ("official", "major")] or [item.source]
            alert = upgrade_alert(fresh, items, confirming, max_links=self.settings.alerts.max_extra_links)
            if await self.dispatcher.send_now(alert):
                self.db.update_story(story_id, told_rank=RANK[new_label])

    async def _retract(self, item_id: int, reason: str) -> None:
        item = self.db.get_item(item_id)
        if item is None or item["story_id"] is None:
            return
        window = self.settings.alerts.retraction_window_minutes * 60
        if self.clock() - item["fetched_at"] > window:
            log.info("retraction.outside_window", extra={"item_id": item_id, "reason": reason})
            return
        async with self._lock:
            story_id = item["story_id"]
            story = self.db.get_story(story_id)
            remaining = self.db.story_items(story_id, include_deleted=False)
            if remaining:
                self.db.update_story(story_id, confidence=self._label(story_id))
            if story["status"] in ("new", "queued", "held") and not remaining:
                self.db.update_story(story_id, status="retracted")
                log.info("story.retracted_before_alert", extra={"story_id": story_id, "reason": reason})
                return
            if story["status"] not in ("alerted", "sending"):
                return
            if not remaining:
                self.db.update_story(story_id, status="retracted")
        louder = story["urgency"] == "urgent" or not remaining
        await self.dispatcher.send_now(retraction_alert(story, item, remaining, reason, louder=louder))
