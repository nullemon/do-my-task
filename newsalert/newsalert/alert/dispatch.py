"""Alert controls: one ring per story, normal-alert spacing, quiet hours, mute.

- urgent  rings immediately, always (also during quiet hours)
- normal  at most one per `normal_min_gap_seconds` (the rest queue); during quiet
          hours they are held and sent as one digest when quiet hours end
- quiet   follow-ups / retractions, sent immediately without sound
- mute    (`newsalert mute 30m`): nothing rings; alerts still arrive silently
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from ..config import QuietHoursSettings, Settings
from ..confidence import RANK
from ..db import Database
from . import Alert, DeliveryResult
from .format import digest_alert

log = logging.getLogger("newsalert.dispatch")

MUTE_KEY = "mute_until"
SendFn = Callable[[Alert], Awaitable[list[DeliveryResult]]]
BuildFn = Callable[[int, str, bool], Alert | None]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.strip().split(":")
    return int(h) * 60 + int(m)


def in_quiet_hours(q: QuietHoursSettings, now: float) -> bool:
    if not q.enabled:
        return False
    tz = ZoneInfo(q.timezone) if q.timezone else None
    local = datetime.fromtimestamp(now, tz) if tz else datetime.fromtimestamp(now)
    cur = local.hour * 60 + local.minute
    start, end = _minutes(q.start), _minutes(q.end)
    if start == end:
        return False
    return start <= cur < end if start < end else (cur >= start or cur < end)


class Dispatcher:
    def __init__(
        self,
        db: Database,
        settings: Settings,
        send: SendFn,
        build_story_alert: BuildFn,
        *,
        clock: Callable[[], float] = time.time,
        echo: bool = True,
    ) -> None:
        self.db = db
        self.settings = settings
        self._send = send
        self._build = build_story_alert
        self.clock = clock
        self.echo = echo
        self._queue: asyncio.Queue = asyncio.Queue()
        self._last_normal_at = 0.0

    # ------------------------------------------------------------------ state

    def mute_until(self) -> float | None:
        raw = self.db.kv_get(MUTE_KEY)
        if raw is None:
            return None
        try:
            until = float(raw)
        except ValueError:
            return None
        return until if until > self.clock() else None

    def is_muted(self) -> bool:
        return self.mute_until() is not None

    def quiet_now(self) -> bool:
        return in_quiet_hours(self.settings.quiet_hours, self.clock())

    # ------------------------------------------------------------------ entry points

    async def ring_story(self, story_id: int, urgency: str) -> None:
        if self.db.story_was_rung(story_id):
            return
        if urgency == "urgent":
            await self._deliver_story(story_id, urgency)
        elif self.quiet_now():
            self.db.update_story(story_id, status="held")
            log.info("story.held", extra={"story_id": story_id, "reason": "quiet hours"})
        else:
            self.db.update_story(story_id, status="queued")
            self._queue.put_nowait(("story", story_id, urgency))

    async def send_now(self, alert: Alert) -> bool:
        """Follow-ups, retractions, tests: no queue, no spacing."""
        if self.is_muted() and alert.urgency != "quiet" and alert.kind != "test":
            alert.urgency = "quiet"
        return await self._deliver(alert)

    async def submit(self, alert: Alert) -> None:
        """A non-story normal alert (e.g. health): spaced like other normal alerts."""
        if self.quiet_now() or self.is_muted():
            alert.urgency = "quiet"
            await self._deliver(alert)
        else:
            self._queue.put_nowait(("alert", alert))

    def restore(self, max_age_s: float = 3600) -> int:
        """Re-queue stories that were waiting to be sent when the process stopped."""
        n = 0
        for row in self.db.stories_with_status("queued"):
            if self.clock() - row["created_at"] <= max_age_s:
                self._queue.put_nowait(("story", row["id"], row["urgency"] or "normal"))
                n += 1
            else:
                self.db.update_story(row["id"], status="expired")
        return n

    # ------------------------------------------------------------------ loops

    async def run(self) -> None:
        """Sender loop for normal alerts: at most one per normal_min_gap_seconds."""
        while True:
            await self.process_one()

    async def process_one(self) -> None:
        job = await self._queue.get()
        gap = self.settings.alerts.normal_min_gap_seconds
        wait = self._last_normal_at + gap - self.clock()
        if wait > 0:
            await asyncio.sleep(wait)
        if job[0] == "story":
            _, story_id, urgency = job
            if self.quiet_now():
                self.db.update_story(story_id, status="held")
                return
            sent = await self._deliver_story(story_id, urgency)
        else:
            sent = await self._deliver(job[1])
        if sent:
            self._last_normal_at = self.clock()

    async def run_flusher(self, every_s: float = 15.0) -> None:
        while True:
            await asyncio.sleep(every_s)
            await self.flush_held()

    async def flush_held(self) -> None:
        if self.quiet_now():
            return
        held = self.db.stories_with_status("held")
        if not held:
            return
        if len(held) == 1:
            await self._deliver_story(held[0]["id"], held[0]["urgency"] or "normal")
            return
        items = {s["id"]: self.db.story_items(s["id"], include_deleted=False) for s in held}
        alert = digest_alert(held, items, reason="during quiet hours", now=self.clock())
        if self.is_muted():
            alert.urgency = "quiet"
        ok = await self._deliver(alert)
        now = self.clock()
        for s in held:
            self.db.update_story(
                s["id"], status="alerted" if ok else "failed", alerted_at=now,
                told_rank=RANK.get(s["confidence"], 0),
            )

    # ------------------------------------------------------------------ delivery

    async def _deliver_story(self, story_id: int, urgency: str) -> bool:
        story = self.db.get_story(story_id)
        if story is None or story["status"] in ("retracted", "dropped", "sending") or self.db.story_was_rung(story_id):
            return False
        alert = self._build(story_id, urgency, self.is_muted())
        if alert is None:
            return False
        # "sending" lets a retraction that arrives mid-send know the ring is on its way.
        self.db.update_story(story_id, status="sending")
        ok = await self._deliver(alert)
        after = self.db.get_story(story_id)
        fields = {"alerted_at": self.clock(), "told_rank": RANK.get(story["confidence"], 0)}
        if after["status"] == "sending":
            fields["status"] = "alerted" if ok else "failed"
        self.db.update_story(story_id, **fields)
        return ok

    async def _deliver(self, alert: Alert) -> bool:
        try:
            results = await self._send(alert)
        except Exception as exc:  # a broken notifier must never kill the pipeline
            log.exception("alert.send_crashed")
            results = [DeliveryResult(ok=False, channel="?", error=f"{type(exc).__name__}: {exc}")]
        ok = any(r.ok for r in results)
        for r in results or [DeliveryResult(ok=False, channel="none", error="no notifiers configured")]:
            self.db.record_alert(
                story_id=alert.story_id, kind=alert.kind, urgency=alert.urgency, title=alert.title,
                message=alert.message, channel=r.channel, ok=r.ok, error=r.error,
            )
        level = logging.INFO if ok else logging.ERROR
        log.log(level, "alert.sent" if ok else "alert.failed", extra={
            "kind": alert.kind, "urgency": alert.urgency, "story_id": alert.story_id, "title": alert.title,
            "channels": {r.channel: r.ok for r in results},
        })
        if self.echo:
            mark = {"urgent": "🔔🔔", "normal": "🔔", "quiet": "·"}[alert.urgency]
            status = "" if ok else "  (DELIVERY FAILED)"
            print(f"\n{mark} {alert.title}{status}\n" + "\n".join(f"  {ln}" for ln in alert.message.splitlines()), flush=True)
        return ok
