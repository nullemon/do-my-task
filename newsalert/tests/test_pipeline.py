"""Ingest behaviour: first-run seeding, stale backlog, exact dedupe, watcher loop."""

import time

import httpx

from newsalert.models import RawItem
from newsalert.watchers.base import WatcherContext
from newsalert.watchers.rss import RssWatcher

from conftest import make_rss, make_source, mock_client


def item(source, title, url, age_s=60, text=None, fetched_at=None):
    fetched_at = fetched_at or time.time()
    return RawItem.from_source(
        source,
        url=url,
        external_id=url,
        title=title,
        text=text or title,
        published_at=None if age_s is None else fetched_at - age_s,
        fetched_at=fetched_at,
    )


async def test_first_poll_seeds_without_alerting(pipeline, sink, db):
    src = make_source()
    items = [item(src, f"Existing story number {i} about something", f"https://e.com/{i}") for i in range(5)]
    stats = await pipeline.ingest(src, items, seeding=True)
    assert stats.seeded == 5 and sink.items == []
    assert db.item_counts() == {"seeded": 5}

    # Same items again on the next poll: duplicates, still silent.
    stats = await pipeline.ingest(src, items, seeding=False)
    assert stats.duplicate == 5 and sink.items == []


async def test_new_item_after_seed_is_emitted(pipeline, sink):
    src = make_source()
    await pipeline.ingest(src, [item(src, "Old story that was already there", "https://e.com/old")], seeding=True)
    fresh = item(src, "Studio X announces Season 2 of Y", "https://e.com/new", age_s=45)
    stats = await pipeline.ingest(src, [fresh], seeding=False)
    assert stats.new == 1
    assert [i.title for _, i in sink.items] == ["Studio X announces Season 2 of Y"]


async def test_backlog_older_than_30_min_is_not_alerted(pipeline, sink, db):
    src = make_source()
    old = item(src, "Something from 31 minutes before fetch", "https://e.com/a", age_s=31 * 60)
    borderline = item(src, "Something from 29 minutes before fetch", "https://e.com/b", age_s=29 * 60)
    stats = await pipeline.ingest(src, [old, borderline], seeding=False)
    assert stats.stale == 1 and stats.new == 1
    assert [i.url for _, i in sink.items] == ["https://e.com/b"]
    assert db.item_counts() == {"new": 1, "stale": 1}


async def test_exact_dedupe_across_sources(pipeline, sink):
    a = make_source("Outlet A")
    b = make_source("Outlet B", url="https://b.example.com/feed")
    await pipeline.ingest(a, [], seeding=True)
    await pipeline.ingest(b, [], seeding=True)

    original = item(a, "Famous actor wins award at festival tonight", "https://a.com/story?utm_source=rss")
    same_url = item(b, "Different headline, same link", "https://www.a.com/story/")
    same_text = item(b, "FAMOUS ACTOR WINS AWARD AT FESTIVAL TONIGHT!", "https://b.com/syndicated")
    await pipeline.ingest(a, [original], seeding=False)
    stats = await pipeline.ingest(b, [same_url, same_text], seeding=False)
    assert stats.duplicate == 2
    assert len(sink.items) == 1


async def test_sink_failure_does_not_break_ingest(db, settings):
    from newsalert.pipeline import Pipeline

    class Boom:
        async def on_new_item(self, *a):
            raise RuntimeError("sink down")

    p = Pipeline(db, settings, Boom())
    src = make_source()
    stats = await p.ingest(src, [item(src, "A story that will hit a broken sink", "https://e.com/x")], seeding=False)
    assert stats.new == 1


async def test_watcher_seeds_then_alerts_and_persists_etag(db, settings, pipeline, sink):
    feeds = [
        make_rss([{"title": "Old headline already in the feed", "link": "https://e.com/old", "age_s": 3600}]),
        make_rss([
            {"title": "Old headline already in the feed", "link": "https://e.com/old", "age_s": 3600},
            {"title": "Breaking: new announcement just now", "link": "https://e.com/new", "age_s": 30},
        ]),
    ]
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers.get("if-none-match"))
        body = feeds[min(len(calls) - 1, 1)]
        return httpx.Response(200, content=body, headers={"ETag": f'"v{len(calls)}"'})

    src = make_source()
    async with mock_client(handler) as client:
        w = RssWatcher(src, WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings), interval=60)
        delay1 = await w.run_once()
        assert sink.items == []  # first poll seeds silently
        assert db.get_source_state(src.name)["seeded"] == 1
        await w.run_once()

    assert [i.title for _, i in sink.items] == ["Breaking: new announcement just now"]
    assert calls == [None, '"v1"']
    assert db.get_source_state(src.name)["etag"] == '"v2"'
    assert 55 <= delay1 <= 65


async def test_watcher_backs_off_on_errors_and_respects_retry_after(db, settings, pipeline):
    responses = [httpx.Response(500), httpx.Response(500), httpx.Response(429, headers={"Retry-After": "600"})]

    async with mock_client(lambda r: responses.pop(0)) as client:
        w = RssWatcher(make_source(), WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings), interval=60)
        d1 = await w.run_once()
        d2 = await w.run_once()
        d3 = await w.run_once()

    assert 54 <= d1 <= 66 and 108 <= d2 <= 132  # exponential backoff
    assert d3 == 600  # server's Retry-After wins
    state = db.get_source_state("Test Feed")
    assert state["consecutive_failures"] == 3 and state["failing_since"] is not None
    assert state["seeded"] == 0  # never seeded, so the first success still won't alert
