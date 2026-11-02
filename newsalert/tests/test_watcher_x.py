"""X API watcher: disabled without a token, lookups, since_id seeding, budget, rate limits."""

import asyncio
import json
import logging

import httpx
import pytest

from newsalert.config import Source
from newsalert.watchers import XWatcher, build_watchers
from newsalert.watchers.base import WatcherContext
from newsalert.watchers.x_api import month_key, next_month_start

from conftest import mock_client

NOW = 1_793_620_800.0  # 2026-11-02T12:00:00Z
TOKEN = "test-bearer-token-abcdef123456"


def x_source(name, account, priority=False, **kw) -> Source:
    return Source(name=name, type="x", account=account, category="anime", trust="official", priority=priority, **kw)


class FakeX:
    """Minimal X API v2: /users/by and /users/:id/tweets."""

    def __init__(self, users=None):
        self.users = users or {"crunchyroll": "100", "mappa_info": "200"}
        self.timelines: dict[str, list[list[dict]]] = {}  # user id -> successive responses
        self.requests: list[httpx.Request] = []
        self.next_response: list[httpx.Response] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        if self.next_response:
            return self.next_response.pop(0)
        path = request.url.path
        if path == "/2/users/by":
            names = request.url.params["usernames"].split(",")
            data = [{"id": self.users[n.lower()], "name": n, "username": n} for n in names if n.lower() in self.users]
            missing = [{"value": n, "title": "Not Found Error"} for n in names if n.lower() not in self.users]
            return httpx.Response(200, json={"data": data, **({"errors": missing} if missing else {})})
        uid = path.split("/")[3]
        pages = self.timelines.get(uid) or [[]]
        posts = pages.pop(0) if len(pages) > 1 else pages[0]
        body = {"data": posts, "meta": {"result_count": len(posts)}} if posts else {"meta": {"result_count": 0}}
        if posts:
            body["meta"]["newest_id"] = posts[0]["id"]
        return httpx.Response(200, json=body, headers={"x-rate-limit-remaining": "99", "x-rate-limit-reset": str(int(NOW + 900))})

    def timeline_calls(self, uid):
        return [r for r in self.requests if r.url.path == f"/2/users/{uid}/tweets"]


def post(pid: str, text: str, age_s: float) -> dict:
    from datetime import datetime, timezone

    created = datetime.fromtimestamp(NOW - age_s, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"id": pid, "text": text, "created_at": created, "edit_history_tweet_ids": [pid]}


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


def make(db, pipeline, settings, client, sources, clock, **x):
    if x:
        settings = settings.model_copy(update={"x": settings.x.model_copy(update=x)})
    ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings)
    return XWatcher(sources, ctx, token=TOKEN, clock=clock)


async def test_disabled_without_token_makes_no_requests(db, settings, pipeline, caplog, monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    calls = []
    async with mock_client(lambda r: calls.append(r) or httpx.Response(200)) as client:
        ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings)
        w = XWatcher([x_source("Crunchyroll (X)", "Crunchyroll")], ctx)
        assert not w.enabled
        with caplog.at_level(logging.INFO, logger="newsalert.watcher.x"):
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(w.run(), 0.2)
    assert calls == []
    assert [r.getMessage() for r in caplog.records].count("watcher.disabled") == 1
    assert db.all_source_states() == []  # no health failures recorded


async def test_token_comes_from_env(db, settings, pipeline, monkeypatch):
    monkeypatch.setenv("X_BEARER_TOKEN", f"  {TOKEN}\n")
    ctx = WatcherContext(db=db, pipeline=pipeline, client=httpx.AsyncClient(), settings=settings)
    w = build_watchers([x_source("A", "a"), x_source("B", "b", priority=True)], ctx)[0]
    assert isinstance(w, XWatcher) and w.enabled and w.name == "x" and len(w.sources) == 2


async def test_lookup_seed_then_alert_with_since_id(db, settings, pipeline, sink, caplog):
    api = FakeX()
    api.timelines["100"] = [
        [post("1002", "Old announcement already on the timeline", 7200), post("1001", "Older post", 9000)],
        [post("1003", "BREAKING: new season of a hit anime announced", 30)],
    ]
    clock = Clock()
    src = x_source("Crunchyroll (X)", "@Crunchyroll", priority=True)
    async with mock_client(api.handler) as client:
        w = make(db, pipeline, settings, client, [src], clock)
        with caplog.at_level(logging.DEBUG):
            assert await w.tick() == 0.0   # handle lookup
            assert await w.tick() == 0.0   # first timeline poll: seeds
            assert sink.items == []
            wait = await w.tick()          # nothing due until the priority interval passes
            assert wait == pytest.approx(300)
            clock.t += wait
            await w.tick()

    assert json.loads(db.kv_get("x:user:crunchyroll")) == {"id": "100", "username": "Crunchyroll"}
    first, second = api.timeline_calls("100")
    assert "since_id" not in first.url.params and first.url.params["max_results"] == "5"
    assert first.url.params["exclude"] == "replies,retweets" and first.url.params["tweet.fields"] == "created_at"
    assert second.url.params["since_id"] == "1002"
    assert [i.title for _, i in sink.items] == ["BREAKING: new season of a hit anime announced"]
    item = sink.items[0][1]
    assert item.url == "https://x.com/Crunchyroll/status/1003" and item.external_id == "1003"
    assert item.published_at == NOW - 30 and item.account == "Crunchyroll"
    assert db.kv_get("x:since:Crunchyroll (X)") == "1003"
    assert w.reads_this_month(NOW) == 3
    state = db.get_source_state("Crunchyroll (X)")
    assert state["seeded"] == 1 and state["failing_since"] is None
    assert all(TOKEN not in r.getMessage() and TOKEN not in str(r.__dict__) for r in caplog.records)


async def test_unknown_handle_is_reported_and_others_still_polled(db, settings, pipeline):
    api = FakeX()
    async with mock_client(api.handler) as client:
        w = make(db, pipeline, settings, client, [x_source("MAPPA (X)", "MAPPA_Info"), x_source("Ghost", "nosuchuser")], Clock())
        await w.tick()
        await w.tick()
    assert db.get_source_state("Ghost")["last_error"].startswith("unknown X handle")
    assert db.get_source_state("Ghost")["failing_since"] is not None
    assert len(api.timeline_calls("200")) == 1


def test_first_polls_are_spread_across_each_interval(db, settings, pipeline):
    sources = [x_source(f"N{i}", f"n{i}") for i in range(4)] + [x_source(f"P{i}", f"p{i}", priority=True) for i in range(2)]
    w = make(db, pipeline, settings, httpx.AsyncClient(), sources, Clock())
    w.schedule(NOW)
    offsets = {a.source.name: a.next_due - NOW for a in w.accounts}
    assert [offsets[f"N{i}"] for i in range(4)] == [0, 450, 900, 1350]   # default_interval 1800
    assert [offsets[f"P{i}"] for i in range(2)] == [0, 150]              # priority_interval 300


async def test_budget_throttles_to_priority_then_stops(db, settings, pipeline, caplog):
    api = FakeX()
    clock = Clock()
    sources = [x_source("Normal", "mappa_info"), x_source("Priority", "crunchyroll", priority=True)]
    async with mock_client(api.handler) as client:
        w = make(db, pipeline, settings, client, sources, clock, monthly_read_budget=100)
        await w.tick()  # lookup
        db.kv_set(month_key(NOW), "90")  # 90 % used
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                clock.t += await w.tick()
        assert api.timeline_calls("200") == []          # normal account skipped
        assert len(api.timeline_calls("100")) >= 1
        assert "x.budget_throttled" in [r.getMessage() for r in caplog.records]

        db.kv_set(month_key(clock.t), "100")  # 100 % used
        before = len(api.requests)
        wait = await w.tick()
        assert len(api.requests) == before
        assert wait == pytest.approx(min(next_month_start(clock.t) - clock.t, 3600) + 1)
        assert "x.budget_exhausted" in [r.getMessage() for r in caplog.records]

        # A new month resets the count.
        clock.t = next_month_start(clock.t) + 10
        w.accounts[0].next_due = w.accounts[1].next_due = clock.t
        await w.tick()
        assert len(api.requests) == before + 1


async def test_429_pauses_until_reset_and_marks_failure(db, settings, pipeline):
    api = FakeX()
    clock = Clock()
    async with mock_client(api.handler) as client:
        w = make(db, pipeline, settings, client, [x_source("Priority", "crunchyroll", priority=True)], clock)
        await w.tick()  # lookup
        api.next_response.append(httpx.Response(429, headers={"x-rate-limit-reset": str(int(NOW + 600)), "x-rate-limit-remaining": "0"}))
        await w.tick()
        state = db.get_source_state("Priority")
        assert state["failing_since"] == NOW and state["last_error"].startswith("RateLimited")
        before = len(api.requests)
        wait = await w.tick()
        assert wait == pytest.approx(601) and len(api.requests) == before  # nothing until the window resets
        clock.t += wait
        await w.tick()
    assert len(api.requests) == before + 1
    assert db.get_source_state("Priority")["failing_since"] is None  # recovered


async def test_retry_after_and_exhausted_window_headers(db, settings, pipeline):
    api = FakeX()
    clock = Clock()
    async with mock_client(api.handler) as client:
        w = make(db, pipeline, settings, client, [x_source("P", "crunchyroll", priority=True)], clock)
        await w.tick()
        api.next_response.append(httpx.Response(429, headers={"Retry-After": "120"}))
        await w.tick()
        assert w.not_before["timeline"] == pytest.approx(NOW + 121)

        clock.t = w.not_before["timeline"]
        w.accounts[0].next_due = clock.t
        api.next_response.append(httpx.Response(
            200, json={"meta": {"result_count": 0}},
            headers={"x-rate-limit-remaining": "0", "x-rate-limit-reset": str(int(clock.t + 300))},
        ))
        await w.tick()
        assert w.not_before["timeline"] == pytest.approx(int(clock.t + 300) + 1)  # remaining 0: wait for reset


async def test_lookup_network_error_retries_in_minutes(db, settings, pipeline):
    api = FakeX()
    clock = Clock()

    def handler(request):
        if not api.requests:
            api.requests.append(request)
            raise httpx.ConnectError("boom")
        return api.handler(request)

    async with mock_client(handler) as client:
        w = make(db, pipeline, settings, client, [x_source("P", "crunchyroll", priority=True)], clock)
        await w.tick()
        assert db.get_source_state("P")["failing_since"] == NOW
        wait = await w.tick()
        assert wait == pytest.approx(300)
        clock.t += wait
        await w.tick()  # lookup succeeds
        await w.tick()  # first poll
    assert db.get_source_state("P")["failing_since"] is None
