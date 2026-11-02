"""Bluesky Jetstream watcher: message handling, handle resolution, reconnect cursor."""

import asyncio
import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
from websockets.asyncio.server import serve

from newsalert.config import Source
from newsalert.watchers import BlueskyWatcher, build_watchers
from newsalert.watchers.base import WatcherContext
from newsalert.watchers.bluesky import choose_published_at, handle_cache_key, parse_created_at

from conftest import mock_client

DID = "did:plc:ann0000000000000000000aa"
NOW = 1_793_620_800.0  # 2026-11-02T12:00:00Z


def bsky_source(name="ANN (Bluesky)", account=DID, **kw) -> Source:
    return Source(name=name, type="bluesky", account=account, category="anime", trust="major", **kw)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def post_event(rkey="3kabc", text="Studio X announces Season 2", *, did=DID, time_us=None, created=None, reply=False, embed=None):
    record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": iso(created if created is not None else NOW - 2)}
    if reply:
        record["reply"] = {"parent": {"uri": "at://x/app.bsky.feed.post/1"}, "root": {"uri": "at://x/app.bsky.feed.post/1"}}
    if embed:
        record["embed"] = embed
    return {
        "did": did,
        "time_us": time_us if time_us is not None else int((NOW - 1) * 1_000_000),
        "kind": "commit",
        "commit": {"rev": "r1", "operation": "create", "collection": "app.bsky.feed.post", "rkey": rkey, "record": record, "cid": "bafy"},
    }


def delete_event(rkey="3kabc", did=DID, time_us=None):
    return {
        "did": did,
        "time_us": time_us if time_us is not None else int(NOW * 1_000_000),
        "kind": "commit",
        "commit": {"rev": "r2", "operation": "delete", "collection": "app.bsky.feed.post", "rkey": rkey},
    }


def make_ctx(db, pipeline, settings, client=None, **bluesky):
    if bluesky:
        settings = settings.model_copy(update={"bluesky": settings.bluesky.model_copy(update=bluesky)})
    return WatcherContext(db=db, pipeline=pipeline, client=client or httpx.AsyncClient(), settings=settings)


# --------------------------------------------------------------------------- pure helpers


def test_published_at_prefers_server_time_unless_created_at_is_sane():
    seen_us = int(NOW * 1_000_000)
    assert choose_published_at(seen_us, NOW - 3, NOW) == NOW - 3            # normal latency: createdAt
    assert choose_published_at(seen_us, NOW - 7200, NOW) == NOW             # skewed clock: server time
    assert choose_published_at(seen_us, NOW + 600, NOW) == NOW              # future: server time
    assert choose_published_at(None, None, NOW) == NOW
    assert parse_created_at("2026-11-02T12:00:00.123456789Z") == NOW + 0.123456
    assert parse_created_at("2026-11-02T12:00:00") == NOW                   # no tz = UTC
    assert parse_created_at("not a date") is None


# --------------------------------------------------------------------------- message handling


async def test_post_create_is_ingested_with_normalized_fields(db, settings, pipeline, sink):
    w = BlueskyWatcher([bsky_source()], make_ctx(db, pipeline, settings), clock=lambda: NOW)
    w._assign(w.sources[0], DID, "animenewsnetwork.com")
    embed = {"$type": "app.bsky.embed.external", "external": {"uri": "https://ann.example/s2", "title": "Season 2 confirmed", "description": "Details inside"}}
    await w.handle_message(json.dumps(post_event(embed=embed)))
    assert len(sink.items) == 1
    item = sink.items[0][1]
    assert item.url == f"https://bsky.app/profile/{DID}/post/3kabc"
    assert item.external_id == f"at://{DID}/app.bsky.feed.post/3kabc"
    assert item.account == "animenewsnetwork.com"
    assert item.title == "Studio X announces Season 2"
    assert "Season 2 confirmed" in item.text and "https://ann.example/s2" in item.text
    assert item.published_at == NOW - 2  # createdAt 1s before time_us: sane, used
    assert item.fetched_at == NOW and item.source_type == "bluesky" and item.trust == "major"
    assert w.position_us == int((NOW - 1) * 1_000_000)


async def test_backdated_created_at_does_not_make_fresh_post_stale(db, settings, pipeline, sink):
    w = BlueskyWatcher([bsky_source()], make_ctx(db, pipeline, settings), clock=lambda: NOW)
    w._assign(w.sources[0], DID, DID)
    await w.handle_message(json.dumps(post_event(created=NOW - 3 * 3600)))  # client clock 3h behind
    assert len(sink.items) == 1 and sink.items[0][1].published_at == NOW - 1


async def test_archive_import_and_replies_are_skipped(db, settings, pipeline, sink):
    w = BlueskyWatcher([bsky_source()], make_ctx(db, pipeline, settings), clock=lambda: NOW)
    w._assign(w.sources[0], DID, DID)
    await w.handle_message(json.dumps(post_event("old1", "Imported from 2019", created=NOW - 400 * 86400)))
    await w.handle_message(json.dumps(post_event("rep1", "Thanks for watching!", reply=True)))
    await w.handle_message(json.dumps(post_event("other", "Not ours", did="did:plc:someoneelse")))
    await w.handle_message("not json")
    assert sink.items == []

    w2 = BlueskyWatcher([bsky_source()], make_ctx(db, pipeline, settings, include_replies=True), clock=lambda: NOW)
    w2._assign(w2.sources[0], DID, DID)
    await w2.handle_message(json.dumps(post_event("rep2", "Reply that we now want to see", reply=True)))
    assert [i.external_id for _, i in sink.items] == [f"at://{DID}/app.bsky.feed.post/rep2"]


async def test_delete_of_tracked_post_retracts(db, settings, pipeline, sink):
    retracted = []

    async def on_retraction(item_id, reason):
        retracted.append((item_id, reason))

    sink.on_retraction = on_retraction
    w = BlueskyWatcher([bsky_source()], make_ctx(db, pipeline, settings), clock=lambda: NOW)
    w._assign(w.sources[0], DID, DID)
    await w.handle_message(json.dumps(post_event()))
    await w.handle_message(json.dumps(delete_event()))
    await w.handle_message(json.dumps(delete_event("never-seen")))  # unknown post: harmless
    item_id = sink.items[0][0]
    assert retracted == [(item_id, "bluesky post deleted")]
    row = db.conn.execute("SELECT deleted_at FROM items WHERE id=?", (item_id,)).fetchone()
    assert row["deleted_at"] is not None


# --------------------------------------------------------------------------- handles


async def test_handles_resolve_once_and_are_cached(db, settings, pipeline):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params.get("handle"))
        if request.url.params.get("handle") == "nobody.example":
            return httpx.Response(400, json={"error": "InvalidRequest", "message": "Unable to resolve handle"})
        return httpx.Response(200, json={"did": DID})

    sources = [bsky_source(account="@AnimeNewsNetwork.com"), bsky_source(name="Ghost", account="nobody.example")]
    async with mock_client(handler) as client:
        w = BlueskyWatcher(sources, make_ctx(db, pipeline, settings, client), clock=lambda: NOW)
        await w.resolve()
        assert w.by_did == {DID: sources[0]} and "Ghost" in w.unresolved
        assert json.loads(db.kv_get(handle_cache_key("animenewsnetwork.com")))["did"] == DID

        w2 = BlueskyWatcher(sources[:1], make_ctx(db, pipeline, settings, client), clock=lambda: NOW + 3600)
        await w2.resolve()
        assert w2.by_did == {DID: sources[0]}
    assert calls == ["animenewsnetwork.com", "nobody.example"]  # second watcher used the cache


async def test_resolve_failure_falls_back_to_stale_cache(db, settings, pipeline):
    db.kv_set(handle_cache_key("apnews.com"), json.dumps({"did": DID, "resolved_at": NOW - 10 * 86400}))
    async with mock_client(lambda r: httpx.Response(503)) as client:
        w = BlueskyWatcher([bsky_source(account="apnews.com")], make_ctx(db, pipeline, settings, client), clock=lambda: NOW)
        await w.resolve()
    assert DID in w.by_did and not w.unresolved


def test_long_did_lists_use_options_update(db, settings, pipeline):
    sources = [bsky_source(name=f"S{i}", account=f"did:plc:{i:024d}") for i in range(3)]
    w = BlueskyWatcher(sources, make_ctx(db, pipeline, settings), clock=lambda: NOW)
    for s in sources:
        w._assign(s, s.account, s.account)
    url, hello = w.build_url()
    assert hello is None and parse_qs(urlsplit(url).query)["wantedDids"] == sorted(s.account for s in sources)

    many = [bsky_source(name=f"M{i}", account=f"did:plc:{i:024d}") for i in range(200)]
    w = BlueskyWatcher(many, make_ctx(db, pipeline, settings), clock=lambda: NOW)
    for s in many:
        w._assign(s, s.account, s.account)
    url, hello = w.build_url()
    q = parse_qs(urlsplit(url).query)
    assert "wantedDids" not in q and q["requireHello"] == ["true"]
    assert hello["type"] == "options_update" and len(hello["payload"]["wantedDids"]) == 200


def test_cursor_is_dropped_when_older_than_stale_window(db, settings, pipeline):
    w = BlueskyWatcher([bsky_source()], make_ctx(db, pipeline, settings), clock=lambda: NOW)
    w.position_us = int((NOW - 60) * 1_000_000)
    assert w.cursor() == int((NOW - 60) * 1_000_000) - 5_000_000
    w.position_us = int((NOW - 3600) * 1_000_000)
    assert w.cursor() is None


# --------------------------------------------------------------------------- fake Jetstream


async def test_stream_ingests_reconnects_with_cursor_and_retracts(db, settings, pipeline, sink):
    paths, sessions = [], [
        [post_event("p1", "Breaking: new anime film announced")],
        [delete_event("p1")],
    ]

    async def jetstream(conn):
        paths.append(conn.request.path)
        for event in sessions[len(paths) - 1]:
            await conn.send(json.dumps(event))
        await conn.close()

    async with serve(jetstream, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        ctx = make_ctx(db, pipeline, settings, jetstream_url=f"ws://127.0.0.1:{port}/subscribe", jetstream_fallback_urls=[])
        w = BlueskyWatcher([bsky_source()], ctx, clock=lambda: NOW)
        retract_calls = []
        real_retract = pipeline.retract

        async def spy(source, external_id, reason):
            retract_calls.append((source, external_id, reason))
            return await real_retract(source, external_id, reason)

        pipeline.retract = spy
        delay1 = await asyncio.wait_for(w.run_once(), 5)
        assert [i.title for _, i in sink.items] == ["Breaking: new anime film announced"]
        assert db.get_source_state("ANN (Bluesky)")["failing_since"] is not None  # quick close = failure
        assert 0.8 <= delay1 <= 1.2

        await asyncio.wait_for(w.run_once(), 5)

    first, second = (parse_qs(urlsplit(p).query) for p in paths)
    assert first["wantedDids"] == [DID] and first["wantedCollections"] == ["app.bsky.feed.post"]
    assert "cursor" not in first
    # Resumes a few seconds before the moment the first connection ended.
    assert second["cursor"] == [str(int(NOW * 1_000_000) - 5_000_000)]
    assert retract_calls == [("ANN (Bluesky)", f"at://{DID}/app.bsky.feed.post/p1", "bluesky post deleted")]
    state = db.get_source_state("ANN (Bluesky)")
    assert state["seeded"] == 1 and state["last_success_at"] == NOW


async def test_stream_sends_options_update_for_many_accounts(db, settings, pipeline):
    received = []

    async def jetstream(conn):
        received.append((conn.request.path, json.loads(await conn.recv())))
        await conn.close()

    many = [bsky_source(name=f"M{i}", account=f"did:plc:{i:024d}") for i in range(200)]
    async with serve(jetstream, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        ctx = make_ctx(db, pipeline, settings, jetstream_url=f"ws://127.0.0.1:{port}/subscribe", jetstream_fallback_urls=[])
        await asyncio.wait_for(BlueskyWatcher(many, ctx, clock=lambda: NOW).run_once(), 5)
    path, hello = received[0]
    assert "requireHello=true" in path
    assert hello["type"] == "options_update" and len(hello["payload"]["wantedDids"]) == 200


async def test_connection_refused_marks_all_sources_failing(db, settings, pipeline):
    ctx = make_ctx(db, pipeline, settings, jetstream_url="ws://127.0.0.1:9/subscribe", jetstream_fallback_urls=[])
    w = BlueskyWatcher([bsky_source(), bsky_source(name="Other", account="did:plc:other00000000000000000000")], ctx)
    d1 = await w.run_once()
    d2 = await w.run_once()
    assert d2 > d1  # exponential backoff
    for name in ("ANN (Bluesky)", "Other"):
        state = db.get_source_state(name)
        assert state["failing_since"] is not None and state["consecutive_failures"] == 2


def test_build_watchers_uses_one_connection_for_all_bluesky_sources(db, settings, pipeline):
    ctx = make_ctx(db, pipeline, settings)
    ws = build_watchers([bsky_source(), bsky_source(name="B2", account="did:plc:b2"), bsky_source(name="Off", enabled=False)], ctx)
    assert len(ws) == 1 and ws[0].name == "bluesky" and [s.name for s in ws[0].sources] == ["ANN (Bluesky)", "B2"]


async def test_quiet_connection_still_refreshes_health(db, settings, pipeline):
    done = asyncio.Event()

    async def jetstream(conn):
        await done.wait()
        await conn.close()

    clock = [NOW]
    async with serve(jetstream, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        ctx = make_ctx(db, pipeline, settings, jetstream_url=f"ws://127.0.0.1:{port}/subscribe", jetstream_fallback_urls=[])
        w = BlueskyWatcher([bsky_source()], ctx, clock=lambda: clock[0])
        w.heartbeat_interval = 0.05
        task = asyncio.create_task(w.run_once())
        await asyncio.sleep(0.1)
        clock[0] = NOW + 120
        await asyncio.sleep(0.2)
        done.set()
        await asyncio.wait_for(task, 5)
    assert db.get_source_state("ANN (Bluesky)")["last_success_at"] == NOW + 120


async def test_dead_connection_resumes_from_last_keepalive_not_now(db, settings, pipeline):
    async def jetstream(conn):
        await conn.send(json.dumps(post_event("p1", "One post then the link dies", time_us=int((NOW - 100) * 1_000_000))))
        conn.transport.abort()  # no close frame: abnormal closure

    async with serve(jetstream, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        ctx = make_ctx(db, pipeline, settings, jetstream_url=f"ws://127.0.0.1:{port}/subscribe", jetstream_fallback_urls=[])
        w = BlueskyWatcher([bsky_source()], ctx, clock=lambda: NOW)
        await asyncio.wait_for(w.run_once(), 5)
    # 40 s of keepalive window rewound, then the usual 5 s overlap.
    assert w.position_us == int((NOW - 40) * 1_000_000)
    assert w.cursor() == int((NOW - 45) * 1_000_000)
