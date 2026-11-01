"""Polling loop with conditional-request state, Retry-After and exponential backoff."""

from __future__ import annotations

import asyncio
import email.utils
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import Settings, Source
from ..db import Database
from ..models import RawItem

log = logging.getLogger("newsalert.watcher")


class RateLimited(Exception):
    def __init__(self, retry_after: float | None, message: str = "rate limited") -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SourceError(Exception):
    """The source answered, but not with something usable."""


def parse_retry_after(value: str | None, now: float | None = None) -> float | None:
    """Retry-After is either delta-seconds or an HTTP date."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    return max(0.0, dt.timestamp() - (now if now is not None else time.time()))


@dataclass
class PollResult:
    items: list[RawItem]
    # source_state fields to persist only after the items were stored safely
    # (e.g. ETag), so a crash mid-ingest can't make us skip items.
    state: dict[str, Any] = field(default_factory=dict)


@dataclass
class WatcherContext:
    db: Database
    pipeline: Any  # Pipeline; Any avoids an import cycle
    client: httpx.AsyncClient
    settings: Settings


class PollingWatcher(ABC):
    def __init__(self, source: Source, ctx: WatcherContext, *, interval: float, start_delay: float = 0.0) -> None:
        self.source = source
        self.ctx = ctx
        self.interval = interval
        self.start_delay = start_delay
        self.failures = 0

    @abstractmethod
    async def poll(self, state: dict[str, Any]) -> PollResult: ...

    async def run(self) -> None:
        await asyncio.sleep(self.start_delay)
        while True:
            delay = await self.run_once()
            await asyncio.sleep(delay)

    async def run_once(self) -> float:
        """Poll once; return seconds to wait before the next poll."""
        db = self.ctx.db
        name = self.source.name
        state = db.get_source_state(name)
        try:
            result = await self.poll(state)
            seeding = not state.get("seeded")
            stats = await self.ctx.pipeline.ingest(self.source, result.items, seeding=seeding)
        except asyncio.CancelledError:
            raise
        except RateLimited as exc:
            wait = self._record_failure(exc, retry_after=exc.retry_after)
            log.warning("watcher.rate_limited", extra={"source": name, "retry_in_s": round(wait)})
            return wait
        except Exception as exc:  # network, HTTP, parse errors: back off, keep going
            wait = self._record_failure(exc)
            log.warning(
                "watcher.error",
                extra={"source": name, "error": _describe(exc), "failures": self.failures, "retry_in_s": round(wait)},
            )
            return wait

        db.update_source_state(
            name,
            **result.state,
            seeded=1,
            last_success_at=time.time(),
            consecutive_failures=0,
            failing_since=None,
            last_error=None,
        )
        if self.failures:
            log.info("watcher.recovered", extra={"source": name, "after_failures": self.failures})
        self.failures = 0
        if stats.new or stats.stale:
            log.debug("watcher.polled", extra={"source": name, **stats.__dict__})
        return self.interval * random.uniform(0.95, 1.05)

    def _record_failure(self, exc: Exception, retry_after: float | None = None) -> float:
        polling = self.ctx.settings.polling
        self.failures += 1
        now = time.time()
        state = self.ctx.db.get_source_state(self.source.name)
        self.ctx.db.update_source_state(
            self.source.name,
            last_error_at=now,
            last_error=_describe(exc)[:500],
            failing_since=state.get("failing_since") or now,
            consecutive_failures=self.failures,
        )
        if retry_after is not None:
            return max(min(retry_after, polling.max_retry_after), self.interval)
        backoff = self.interval * (2 ** (self.failures - 1))
        return min(backoff, polling.max_backoff) * random.uniform(0.9, 1.1)


def _describe(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    text = str(exc)
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__
