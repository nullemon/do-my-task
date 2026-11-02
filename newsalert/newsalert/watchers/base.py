"""Watcher bases: a polling loop (conditional requests, Retry-After, exponential
backoff) and a reconnecting stream loop, plus per-source health bookkeeping."""

from __future__ import annotations

import asyncio
import email.utils
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol

import httpx

from ..config import Settings, Source, Watchlist
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
    watchlist: Watchlist = field(default_factory=Watchlist)


class PollingWatcher(ABC):
    def __init__(self, source: Source, ctx: WatcherContext, *, interval: float, start_delay: float = 0.0) -> None:
        self.source = source
        self.ctx = ctx
        self.interval = interval
        self.start_delay = start_delay
        self.failures = 0

    @property
    def name(self) -> str:
        return self.source.name

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


# --------------------------------------------------------------------------- streams


class Watcher(Protocol):
    """What main.py runs: one asyncio task per watcher object."""

    @property
    def name(self) -> str: ...

    async def run(self) -> None: ...


class StreamEnded(Exception):
    """The server closed a long-lived stream."""


class SourceHealth:
    """Keeps `source_state` accurate for sources served by one stream or scheduler.

    The health checker alerts when `failing_since` is older than N minutes, so every
    failure sets it (keeping the first timestamp) and every success clears it.
    """

    def __init__(self, db: Database, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.clock = clock

    def ok(self, names: Iterable[str]) -> None:
        now = self.clock()
        for name in names:
            self.db.update_source_state(
                name,
                seeded=1,
                last_success_at=now,
                consecutive_failures=0,
                failing_since=None,
                last_error=None,
            )

    def failed(self, names: Iterable[str], error: str) -> None:
        now = self.clock()
        for name in names:
            state = self.db.get_source_state(name)
            self.db.update_source_state(
                name,
                last_error_at=now,
                last_error=error[:500],
                failing_since=state.get("failing_since") or now,
                consecutive_failures=(state.get("consecutive_failures") or 0) + 1,
            )


class StreamWatcher(ABC):
    """A long-lived connection (websocket / SSE) that serves one or more sources.

    Subclasses implement `connect_once()`: connect, call `self.connected()` once the
    stream is up, call `self.alive()` on traffic, and return (or raise) when it ends.
    `run()` reconnects forever with exponential backoff (1s, 2s, 4s ... capped), and
    resets the backoff after a connection that stayed up for `healthy_after` seconds.
    """

    min_backoff: float = 1.0
    max_backoff: float = 300.0
    healthy_after: float = 60.0      # a connection up this long counts as healthy
    heartbeat_interval: float = 60.0  # how often traffic refreshes last_success_at

    def __init__(
        self,
        ctx: WatcherContext,
        sources: list[Source],
        *,
        name: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.ctx = ctx
        self.sources = sources
        self._name = name
        self.clock = clock
        self.health = SourceHealth(ctx.db, clock)
        self.failures = 0
        self._connected_at: float | None = None
        self._last_ok_at = 0.0

    @property
    def name(self) -> str:
        return self._name

    @property
    def source_names(self) -> list[str]:
        return [s.name for s in self.sources]

    @abstractmethod
    async def connect_once(self) -> None: ...

    def connected(self, names: Iterable[str] | None = None) -> None:
        now = self.clock()
        self._connected_at = now
        self._last_ok_at = now
        self.health.ok(self.source_names if names is None else names)
        if self.failures:
            log.info("watcher.recovered", extra={"watcher": self.name, "after_failures": self.failures})

    def healthy_names(self) -> list[str]:
        """Sources to refresh on traffic (subclasses drop ones that are broken)."""
        return self.source_names

    def alive(self) -> None:
        now = self.clock()
        if now - self._last_ok_at >= self.heartbeat_interval:
            self._last_ok_at = now
            self.health.ok(self.healthy_names())

    async def run(self) -> None:
        while True:
            delay = await self.run_once()
            await asyncio.sleep(delay)

    async def run_once(self) -> float:
        """One connection attempt; returns seconds to wait before reconnecting."""
        self._connected_at = None
        try:
            await self.connect_once()
            exc: Exception = StreamEnded("stream closed by server")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # network, HTTP, protocol: reconnect with backoff
            exc = e
        now = self.clock()
        was_healthy = self._connected_at is not None and now - self._connected_at >= self.healthy_after
        if was_healthy:
            self.failures = 0
            if isinstance(exc, StreamEnded):
                # Normal for long-lived streams (servers recycle connections): reconnect
                # right away; if that fails, the failure is recorded then.
                log.info("watcher.stream_reconnect", extra={"watcher": self.name})
                return self.min_backoff
        self.failures += 1
        self.health.failed(self.source_names, _describe(exc))
        cap = min(self.max_backoff, self.ctx.settings.polling.max_backoff)
        delay = min(self.min_backoff * (2 ** (self.failures - 1)), cap) * random.uniform(0.9, 1.1)
        if isinstance(exc, RateLimited) and exc.retry_after is not None:
            delay = max(delay, min(exc.retry_after, self.ctx.settings.polling.max_retry_after))
        log.warning(
            "watcher.stream_error",
            extra={"watcher": self.name, "error": _describe(exc), "failures": self.failures, "retry_in_s": round(delay, 1)},
        )
        return delay


def load_json(value: str | None) -> dict | None:
    """Parse a JSON object stored in kv; None if missing or malformed."""
    if not value:
        return None
    try:
        data = json.loads(value)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None
