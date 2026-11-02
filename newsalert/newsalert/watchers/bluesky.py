"""Bluesky watcher: one Jetstream websocket for every Bluesky source.

Jetstream is Bluesky's free, public JSON firehose. We subscribe only to
`app.bsky.feed.post` records of the DIDs we follow, so traffic is tiny. No keys,
no login. Reposts live in another collection, so they never arrive.

Sources list a handle (`account: variety.com`) or a DID (`account: did:plc:...`).
Handles are resolved once via the public `com.atproto.identity.resolveHandle`
endpoint and cached in the kv table.

Timestamps (`published_at`)
    A post record's `createdAt` is set by the poster's client and can be anything:
    skewed device clocks, timezone bugs and "archive importers" that copy years-old
    tweets into Bluesky all produce backdated values. The pipeline drops items whose
    `published_at` is >30 min before fetch, so trusting `createdAt` could silently
    hide a fresh post. We therefore use the event's `time_us` (the Jetstream
    server's clock when the post reached the network) and only take `createdAt`
    when it is a few minutes *earlier* than that (normal client->relay latency).
    `time_us` also keeps replays honest: posts replayed from a reconnect cursor
    carry their original time and are treated as stale if they are old.
    Posts whose `createdAt` is more than a day before `time_us` are archive imports
    (Bluesky shows them as "Archived from ..."), not breaking news, and are skipped.

Reconnects resume from a `cursor`: a few seconds before the last moment we know
the connection was delivering (now, after a clean close; the last keepalive,
after a dead link), so a short disconnect doesn't lose posts. Duplicates from the
overlap are deduped by the post's at:// URI.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode

import websockets
from websockets.asyncio.client import connect as ws_connect

from ..config import Source
from ..models import RawItem
from ..text import truncate
from .base import SourceError, StreamWatcher, WatcherContext, load_json

log = logging.getLogger("newsalert.watcher.bluesky")

POST_COLLECTION = "app.bsky.feed.post"
_CURSOR_REWIND_US = 5_000_000          # resume a few seconds early; overlap is deduped
_CREATED_AT_SLACK_S = 300              # createdAt may precede time_us by this much
_ARCHIVED_AFTER_S = 24 * 3600          # createdAt older than this vs time_us = import
_MAX_URL_LEN = 1800                    # beyond this, send DIDs in an options_update
_PING_INTERVAL_S = 20                  # websocket keepalive: a dead link is noticed within
_PING_TIMEOUT_S = 20                   # interval + timeout seconds
_MAX_TEXT = 1500
_CURSOR_KV = "bluesky:cursor"
_FRACTION = re.compile(r"(\.\d{6})\d+")


def handle_cache_key(handle: str) -> str:
    return f"bluesky:did:{handle}"


def normalize_account(account: str) -> str:
    value = account.strip()
    if value.startswith("https://bsky.app/profile/"):
        value = value.removeprefix("https://bsky.app/profile/").split("/")[0]
    return value.lstrip("@").lower() if not value.startswith("did:") else value


def parse_created_at(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    text = _FRACTION.sub(r"\1", value.strip().replace("Z", "+00:00").replace("z", "+00:00"))
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def choose_published_at(time_us: Any, created_at: float | None, now: float) -> float:
    """See the module docstring: trust the server's time, use createdAt only if sane."""
    seen = time_us / 1_000_000 if isinstance(time_us, (int, float)) and time_us > 0 else now
    if created_at is not None and seen - _CREATED_AT_SLACK_S <= created_at <= seen:
        return created_at
    return seen


def post_url(did: str, rkey: str) -> str:
    return f"https://bsky.app/profile/{did}/post/{rkey}"


def post_uri(did: str, rkey: str) -> str:
    return f"at://{did}/{POST_COLLECTION}/{rkey}"


def _embed_text(embed: Any) -> str:
    """Text of a link card (title, description, URL) so triage sees what's linked."""
    if not isinstance(embed, dict):
        return ""
    if embed.get("$type") == "app.bsky.embed.recordWithMedia":
        embed = embed.get("media") or {}
    external = embed.get("external") if isinstance(embed, dict) else None
    if not isinstance(external, dict):
        return ""
    parts = [external.get("title") or "", external.get("description") or "", external.get("uri") or ""]
    return "\n".join(p.strip() for p in parts if p and p.strip())


class BlueskyWatcher(StreamWatcher):
    def __init__(
        self,
        sources: list[Source],
        ctx: WatcherContext,
        *,
        clock: Callable[[], float] = time.time,
        connect: Callable[..., Any] = ws_connect,
    ) -> None:
        super().__init__(ctx, sources, name="bluesky", clock=clock)
        self.cfg = ctx.settings.bluesky
        self._connect = connect
        self.by_did: dict[str, Source] = {}
        self.display: dict[str, str] = {}       # did -> handle shown in items
        self.unresolved: dict[str, str] = {}    # source name -> why
        self.position_us: int | None = None     # newest time_us we have fully seen
        self._saved_position_at = 0.0
        self._url_index = 0
        self._load_cursor()

    # ------------------------------------------------------------------ handles

    async def resolve(self) -> None:
        """Map every source to a DID (cached in kv). Unresolvable sources stay failing."""
        now = self.clock()
        max_age = self.cfg.handle_cache_hours * 3600
        db = self.ctx.db
        for source in self.sources:
            if any(s is source for s in self.by_did.values()):
                continue
            account = normalize_account(source.account or "")
            if account.startswith("did:"):
                self._assign(source, account, account)
                continue
            cached = load_json(db.kv_get(handle_cache_key(account)))
            did = cached.get("did") if cached else None
            if did and now - float(cached.get("resolved_at") or 0) < max_age:
                self._assign(source, did, account)
                continue
            try:
                did = await self._resolve_handle(account)
            except Exception as exc:  # network / bad handle
                if cached and cached.get("did"):
                    log.warning("bluesky.resolve_failed_using_cache", extra={"source": source.name, "error": str(exc)[:200]})
                    self._assign(source, cached["did"], account)
                else:
                    self.unresolved[source.name] = f"cannot resolve handle {account!r}: {exc}"[:300]
                    log.warning("bluesky.resolve_failed", extra={"source": source.name, "handle": account, "error": str(exc)[:200]})
                continue
            db.kv_set(handle_cache_key(account), json.dumps({"did": did, "resolved_at": now}))
            self._assign(source, did, account)

    async def _resolve_handle(self, handle: str) -> str:
        resp = await self.ctx.client.get(self.cfg.resolve_url, params={"handle": handle})
        if resp.status_code == 400:
            raise SourceError("handle not found")
        resp.raise_for_status()
        did = resp.json().get("did")
        if not isinstance(did, str) or not did.startswith("did:"):
            raise SourceError("no did in response")
        return did

    def _assign(self, source: Source, did: str, display: str) -> None:
        other = self.by_did.get(did)
        if other is not None and other is not source:
            self.unresolved[source.name] = f"same account as source {other.name!r}"
            log.warning("bluesky.duplicate_account", extra={"source": source.name, "other": other.name})
            return
        self.by_did[did] = source
        self.display[did] = display
        self.unresolved.pop(source.name, None)

    def healthy_names(self) -> list[str]:
        return [s.name for s in self.by_did.values()]

    # ------------------------------------------------------------------ connection

    def _base_url(self) -> str:
        urls = [self.cfg.jetstream_url, *self.cfg.jetstream_fallback_urls]
        return urls[self._url_index % len(urls)]

    def cursor(self) -> int | None:
        """Where to resume: a few seconds before the last moment we know we saw everything."""
        if self.position_us is None:
            return None
        max_age = self.ctx.settings.pipeline.stale_minutes * 60
        if self.clock() - self.position_us / 1_000_000 > max_age:
            return None  # anything older would be stale anyway: go live
        return self.position_us - _CURSOR_REWIND_US

    def build_url(self) -> tuple[str, dict[str, Any] | None]:
        """Subscribe URL, plus an options_update message when the DID list is too long for it."""
        dids = sorted(self.by_did)
        cursor = self.cursor()
        tail = [("cursor", str(cursor))] if cursor is not None else []
        params = [("wantedCollections", POST_COLLECTION), *(("wantedDids", d) for d in dids), *tail]
        url = f"{self._base_url()}?{urlencode(params)}"
        if len(url) <= _MAX_URL_LEN:
            return url, None
        # requireHello pauses the stream until our filter arrives, so nothing unfiltered leaks.
        params = [("wantedCollections", POST_COLLECTION), ("requireHello", "true"), *tail]
        hello = {
            "type": "options_update",
            "payload": {"wantedCollections": [POST_COLLECTION], "wantedDids": dids, "maxMessageSizeBytes": 0},
        }
        return f"{self._base_url()}?{urlencode(params)}", hello

    async def connect_once(self) -> None:
        if self.unresolved or not self.by_did:
            await self.resolve()
        if not self.by_did:
            raise SourceError("no Bluesky account could be resolved")
        if self.failures >= 2:  # this instance keeps failing: try the next official one
            self._url_index += 1
        url, hello = self.build_url()
        clean = False
        try:
            async with self._connect(
                url,
                user_agent_header=self.ctx.settings.polling.user_agent,
                open_timeout=15,
                ping_interval=_PING_INTERVAL_S,
                ping_timeout=_PING_TIMEOUT_S,
                close_timeout=5,
            ) as ws:
                if hello is not None:
                    await ws.send(json.dumps(hello))
                self.connected(self.healthy_names())
                if self.unresolved:
                    self.health.failed(list(self.unresolved), "; ".join(self.unresolved.values()))
                log.info(
                    "bluesky.connected",
                    extra={"accounts": len(self.by_did), "cursor": self.cursor() is not None, "instance": self._base_url()},
                )
                heartbeat = asyncio.create_task(self._heartbeat())
                try:
                    async for message in ws:
                        await self.handle_message(message)
                        self.alive()
                    clean = True
                except websockets.ConnectionClosedOK:
                    clean = True
                finally:
                    heartbeat.cancel()
        finally:
            if self._connected_at is not None:
                # Resume even if no post arrived: after a clean close we saw everything
                # up to now; after a dead connection only up to the last keepalive.
                alive_until = self.clock() - (0 if clean else _PING_INTERVAL_S + _PING_TIMEOUT_S)
                self.position_us = max(self.position_us or 0, int(alive_until * 1_000_000))
                self._save_cursor(force=True)

    async def _heartbeat(self) -> None:
        # Posts from a handful of accounts can be hours apart. While the socket is
        # open (websockets' keepalive pings close it if the server goes away), keep
        # last_success_at fresh anyway.
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            self.alive()

    # ------------------------------------------------------------------ messages

    async def handle_message(self, raw: str | bytes) -> None:
        try:
            event = json.loads(raw)
        except (TypeError, ValueError):
            log.debug("bluesky.bad_message")
            return
        if not isinstance(event, dict):
            return
        did = event.get("did")
        source = self.by_did.get(did) if isinstance(did, str) else None
        kind = event.get("kind")
        if kind == "commit" and source is not None:
            commit = event.get("commit") or {}
            if commit.get("collection") == POST_COLLECTION and isinstance(commit.get("rkey"), str):
                op = commit.get("operation")
                if op == "create":
                    item = self.post_to_item(source, did, commit, event.get("time_us"))
                    if item is not None:
                        await self.ctx.pipeline.ingest(source, [item], seeding=False)
                elif op == "delete":
                    await self.ctx.pipeline.retract(source.name, post_uri(did, commit["rkey"]), "bluesky post deleted")
        elif kind == "identity" and source is not None:
            handle = (event.get("identity") or {}).get("handle")
            if isinstance(handle, str) and handle and handle != self.display.get(did):
                log.info("bluesky.handle_changed", extra={"source": source.name, "handle": handle})
                self.display[did] = handle
        elif kind == "account" and source is not None:
            account = event.get("account") or {}
            if account.get("active") is False:
                log.warning("bluesky.account_inactive", extra={"source": source.name, "status": account.get("status")})
        time_us = event.get("time_us")
        if isinstance(time_us, int) and time_us > (self.position_us or 0):
            self.position_us = time_us
            self._save_cursor()

    def post_to_item(self, source: Source, did: str, commit: dict, time_us: Any) -> RawItem | None:
        record = commit.get("record") or {}
        if not isinstance(record, dict):
            return None
        if record.get("reply") and not self.cfg.include_replies:
            return None
        now = self.clock()
        created = parse_created_at(record.get("createdAt"))
        seen = time_us / 1_000_000 if isinstance(time_us, (int, float)) and time_us > 0 else now
        if created is not None and seen - created > _ARCHIVED_AFTER_S:
            log.info("bluesky.archived_post_skipped", extra={"source": source.name, "rkey": commit["rkey"]})
            return None
        rkey = commit["rkey"]
        handle = self.display.get(did) or did
        text = (record.get("text") or "").strip()
        body = "\n".join(p for p in (text, _embed_text(record.get("embed"))) if p)
        first_line = next((ln for ln in body.splitlines() if ln.strip()), "")
        return RawItem.from_source(
            source,
            url=post_url(did, rkey),
            account=handle,
            external_id=post_uri(did, rkey),
            title=truncate(first_line, 140) or f"New post by @{handle}",
            text=truncate(body or f"New post by @{handle} (no text)", _MAX_TEXT),
            published_at=choose_published_at(time_us, created, now),
            fetched_at=now,
        )

    # ------------------------------------------------------------------ cursor persistence

    def _load_cursor(self) -> None:
        data = load_json(self.ctx.db.kv_get(_CURSOR_KV))
        value = data.get("time_us") if data else None
        if isinstance(value, int):
            self.position_us = value

    def _save_cursor(self, force: bool = False) -> None:
        now = self.clock()
        if self.position_us is None or (not force and now - self._saved_position_at < 10):
            return
        self._saved_position_at = now
        self.ctx.db.kv_set(_CURSOR_KV, json.dumps({"time_us": self.position_us}))
