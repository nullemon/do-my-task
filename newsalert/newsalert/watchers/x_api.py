"""X (Twitter) watcher: official X API v2 only, one scheduler for every X source.

Reading timelines needs a paid API tier. Without `X_BEARER_TOKEN` in the
environment this watcher logs `watcher.disabled` once and idles: no requests, no
health failures. With a token:

* handles -> user ids via `GET /2/users/by?usernames=` (cached in kv);
* each account polled with `GET /2/users/:id/tweets?since_id=...` excluding
  replies and reposts. `priority: true` accounts every `x.priority_interval`,
  others every `x.default_interval`; first polls are spread evenly across the
  interval so requests never bunch up;
* the first poll of an account only records the newest post id (seeding);
* `x-rate-limit-remaining` / `x-rate-limit-reset` and 429s pause the endpoint
  until the window resets;
* a monthly read budget (`x.monthly_read_budget`, counted per UTC calendar month
  in kv): at 90 % only priority accounts are polled, at 100 % nothing until the
  next month.

The token is only ever put in the Authorization header of our own requests and
is never logged.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from ..config import Source
from ..models import RawItem
from ..text import truncate
from .base import RateLimited, SourceError, SourceHealth, WatcherContext, _describe, load_json, parse_retry_after

log = logging.getLogger("newsalert.watcher.x")

_TIMELINE = "timeline"
_USERS = "users"
_THROTTLE_AT = 0.9       # share of the monthly budget after which only priority accounts are polled
_SEED_RESULTS = 5        # the API's minimum page size; seeding needs only the newest id
_LOOKUP_RETRY_S = 3600   # retry lookups of unknown handles this often
_LOOKUP_ERROR_RETRY_S = 300  # ... and after a network/API error
_DEFAULT_RATE_PAUSE_S = 900  # 429 without reset headers: X windows are 15 minutes
_MAX_TEXT = 1500


def month_key(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).strftime("x:reads:%Y-%m")


def next_month_start(now: float) -> float:
    dt = datetime.fromtimestamp(now, timezone.utc)
    year, month = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return datetime(year, month, 1, tzinfo=timezone.utc).timestamp()


def _parse_time(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


@dataclass(order=True)
class _Account:
    next_due: float
    seq: int
    source: Source = field(compare=False)
    handle: str = field(compare=False)
    interval: float = field(compare=False)
    user_id: str | None = field(default=None, compare=False)
    username: str | None = field(default=None, compare=False)
    failures: int = field(default=0, compare=False)


class XWatcher:
    def __init__(
        self,
        sources: list[Source],
        ctx: WatcherContext,
        *,
        token: str | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.ctx = ctx
        self.cfg = ctx.settings.x
        self.sources = sources
        self.clock = clock
        self._token = (token if token is not None else os.environ.get("X_BEARER_TOKEN", "")).strip()
        self.health = SourceHealth(ctx.db, clock)
        self.accounts: list[_Account] = []
        self.not_before: dict[str, float] = {}    # endpoint -> epoch when we may call it again
        self._lookup_due = 0.0
        self._logged_mode: tuple[str, str] | None = None
        self._scheduled = False

    @property
    def name(self) -> str:
        return "x"

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    async def run(self) -> None:
        if not self.enabled:
            log.info(
                "watcher.disabled",
                extra={"watcher": "x", "reason": "X_BEARER_TOKEN is not set", "sources": len(self.sources)},
            )
            await asyncio.Event().wait()  # idle forever without touching the network
            return
        log.info("x.started", extra={"accounts": len(self.sources), "priority": sum(s.priority for s in self.sources)})
        while True:
            try:
                delay = await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("x.scheduler_error")
                delay = 60.0
            await asyncio.sleep(max(delay, 0.0))

    # ------------------------------------------------------------------ scheduling

    def schedule(self, now: float) -> None:
        """Spread each interval group's first polls evenly across its interval."""
        groups: dict[float, list[Source]] = {}
        for s in self.sources:
            interval = float(self.cfg.priority_interval if s.priority else self.cfg.default_interval)
            if s.interval:  # a per-source interval still wins, but never below the floor
                interval = float(max(s.interval, self.ctx.settings.polling.min_interval))
            groups.setdefault(interval, []).append(s)
        seq = 0
        for interval, members in groups.items():
            for idx, s in enumerate(members):
                handle = (s.account or "").strip().lstrip("@")
                self.accounts.append(
                    _Account(next_due=now + interval * idx / len(members), seq=seq, source=s, handle=handle, interval=interval)
                )
                seq += 1
        self._load_cached_ids()
        self._scheduled = True

    def budget_mode(self, now: float) -> str:
        """'ok', 'priority_only' (>= 90 % used) or 'exhausted' (100 %)."""
        budget = self.cfg.monthly_read_budget
        used = self.reads_this_month(now)
        if budget <= 0 or used >= budget:
            mode = "exhausted"
        elif used >= budget * _THROTTLE_AT:
            mode = "priority_only"
        else:
            mode = "ok"
        key = (month_key(now), mode)
        if mode != "ok" and self._logged_mode != key:
            event = "x.budget_exhausted" if mode == "exhausted" else "x.budget_throttled"
            log.warning(event, extra={"used": used, "budget": budget, "month": key[0][-7:]})
        self._logged_mode = key
        return mode

    def reads_this_month(self, now: float) -> int:
        return int(self.ctx.db.kv_get(month_key(now)) or 0)

    def _count_reads(self, n: int, now: float) -> None:
        if n > 0:
            self.ctx.db.kv_set(month_key(now), str(self.reads_this_month(now) + n))

    async def tick(self) -> float:
        """Do at most one request; return seconds until something is due."""
        now = self.clock()
        if not self._scheduled:
            self.schedule(now)
        if not self.accounts:
            return 3600.0
        mode = self.budget_mode(now)
        if mode == "exhausted":
            return min(next_month_start(now) - now, 3600.0) + 1

        unresolved = any(a.user_id is None for a in self.accounts)
        if unresolved and now >= self._lookup_due:
            if now >= self.not_before.get(_USERS, 0):
                await self._lookup_users(now)
                return 0.0
            self._lookup_due = self.not_before[_USERS]

        waits = []
        eligible = [a for a in self.accounts if a.user_id and (mode == "ok" or a.source.priority)]
        if eligible:
            account = min(eligible)
            due = max(account.next_due, self.not_before.get(_TIMELINE, 0))
            if due <= now:
                await self._poll(account, now)
                return 0.0
            waits.append(due - now)
        if unresolved:
            waits.append(self._lookup_due - now)
        return max(min(waits, default=3600.0), 0.5)

    # ------------------------------------------------------------------ requests

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "User-Agent": self.ctx.settings.polling.user_agent}

    async def _get(self, endpoint: str, path: str, params: dict[str, Any], now: float) -> dict:
        resp = await self.ctx.client.get(f"{self.cfg.api_base}{path}", params=params, headers=self._headers())
        self._note_rate_limit(endpoint, resp, now)
        if resp.status_code == 429:
            reset = self.not_before.get(endpoint)
            raise RateLimited(None if reset is None else max(reset - now, 0), "HTTP 429")
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError as exc:
            raise SourceError("X API returned non-JSON") from exc

    def _note_rate_limit(self, endpoint: str, resp: httpx.Response, now: float) -> None:
        """Pause an endpoint when its window is used up (remaining == 0) or on 429."""
        reset_header = (resp.headers.get("x-rate-limit-reset") or "").strip()
        reset = float(reset_header) if reset_header.isdigit() else None
        if resp.status_code == 429:
            retry_after = parse_retry_after(resp.headers.get("retry-after"), now=now)
            candidates = [t for t in (reset, None if retry_after is None else now + retry_after) if t and t > now]
            until = max(candidates) if candidates else now + _DEFAULT_RATE_PAUSE_S
        elif (resp.headers.get("x-rate-limit-remaining") or "").strip() == "0" and reset and reset > now:
            until = reset
        else:
            return
        until = min(until, now + self.ctx.settings.polling.max_retry_after) + 1
        self.not_before[endpoint] = max(self.not_before.get(endpoint, 0), until)
        log.info("x.rate_limit_pause", extra={"endpoint": endpoint, "resume_in_s": round(until - now)})

    def _load_cached_ids(self) -> None:
        for a in self.accounts:
            cached = load_json(self.ctx.db.kv_get(f"x:user:{a.handle.lower()}"))
            if cached and cached.get("id"):
                a.user_id = str(cached["id"])
                a.username = cached.get("username") or a.handle

    async def _lookup_users(self, now: float) -> None:
        missing = [a for a in self.accounts if a.user_id is None]
        self._lookup_due = now + _LOOKUP_RETRY_S
        for start in range(0, len(missing), 100):
            batch = missing[start:start + 100]
            try:
                data = await self._get(_USERS, "/users/by", {"usernames": ",".join(a.handle for a in batch)}, now)
            except Exception as exc:  # transient: retry sooner than for unknown handles
                self._lookup_due = max(now + _LOOKUP_ERROR_RETRY_S, self.not_before.get(_USERS, 0))
                self.health.failed([a.source.name for a in batch], f"user lookup failed: {_describe(exc)}")
                log.warning("x.lookup_failed", extra={"error": _describe(exc), "accounts": len(batch)})
                return
            found = {u["username"].lower(): u for u in data.get("data") or [] if u.get("username") and u.get("id")}
            for a in batch:
                user = found.get(a.handle.lower())
                if user is None:
                    self.health.failed([a.source.name], f"unknown X handle {a.handle!r}")
                    log.warning("x.unknown_handle", extra={"source": a.source.name, "handle": a.handle})
                    continue
                a.user_id, a.username = str(user["id"]), user["username"]
                self.ctx.db.kv_set(f"x:user:{a.handle.lower()}", json.dumps({"id": a.user_id, "username": a.username}))

    async def _poll(self, account: _Account, now: float) -> None:
        name = account.source.name
        since_key = f"x:since:{name}"
        since_id = self.ctx.db.kv_get(since_key)
        seeding = not self.ctx.db.get_source_state(name).get("seeded")
        params: dict[str, Any] = {
            "exclude": "replies,retweets",
            "tweet.fields": "created_at",
            "max_results": _SEED_RESULTS if seeding or not since_id else max(5, min(self.cfg.max_results, 100)),
        }
        if since_id:
            params["since_id"] = since_id
        try:
            data = await self._get(_TIMELINE, f"/users/{account.user_id}/tweets", params, now)
            posts = [p for p in data.get("data") or [] if isinstance(p, dict) and p.get("id")]
            self._count_reads(len(posts), now)
            items = [self._to_item(account, p, now) for p in posts]
            await self.ctx.pipeline.ingest(account.source, items, seeding=seeding)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            account.failures += 1
            self.health.failed([name], _describe(exc))
            backoff = account.interval * (2 ** (account.failures - 1))
            delay = min(backoff, max(account.interval, self.ctx.settings.polling.max_backoff)) * random.uniform(0.95, 1.05)
            if isinstance(exc, RateLimited):
                delay = max(delay, self.not_before.get(_TIMELINE, now) - now)
            self._reschedule(account, now + delay)
            log.warning("watcher.error", extra={"source": name, "error": _describe(exc), "retry_in_s": round(delay)})
            return
        newest = (data.get("meta") or {}).get("newest_id") or (posts[0]["id"] if posts else None)
        if newest and (not since_id or int(newest) > int(since_id)):
            self.ctx.db.kv_set(since_key, str(newest))
        self.health.ok([name])
        if account.failures:
            log.info("watcher.recovered", extra={"source": name, "after_failures": account.failures})
        account.failures = 0
        next_due = account.next_due + account.interval
        if next_due <= now:  # fell behind (budget pause, rate limit): restart, re-spread
            next_due = now + account.interval * random.uniform(0.5, 1.0)
        self._reschedule(account, next_due)

    def _reschedule(self, account: _Account, next_due: float) -> None:
        account.next_due = next_due

    def _to_item(self, account: _Account, post: dict, now: float) -> RawItem:
        username = account.username or account.handle
        text = html.unescape(post.get("text") or "").strip()
        return RawItem.from_source(
            account.source,
            url=f"https://x.com/{username}/status/{post['id']}",
            account=username,
            external_id=str(post["id"]),
            title=truncate(text.splitlines()[0] if text else f"New post by @{username}", 140),
            text=truncate(text or f"New post by @{username}", _MAX_TEXT),
            published_at=_parse_time(post.get("created_at")),
            fetched_at=now,
        )
