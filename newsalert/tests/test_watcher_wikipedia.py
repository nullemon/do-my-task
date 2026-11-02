"""Wikipedia EventStreams watcher: SSE, page filtering, diff extraction, revert -> retract."""

import json
from pathlib import Path

import httpx
import pytest

from newsalert.config import Source, Watchlist, WatchlistEntry
from newsalert.watchers import WikipediaWatcher, build_watchers
from newsalert.watchers.base import WatcherContext
from newsalert.watchers.wikipedia import (
    DiffRow,
    deaths_titles,
    has_contact,
    iter_sse,
    new_death_entries,
    normalize_title,
    parse_diff,
    watch_signals,
    wikitext_to_plain,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOW = 1_793_620_800.0          # 2026-11-02T12:00:00Z
NOV_30_LATE = 1_796_083_140.0  # 2026-11-30T23:59:00Z
DEC_1_EARLY = 1_796_083_260.0  # 2026-12-01T00:01:00Z
DEATHS_DIFF = (FIXTURES / "wiki_deaths_diff.html").read_text(encoding="utf-8")
PERSON_DIFF = (FIXTURES / "wiki_person_death_diff.html").read_text(encoding="utf-8")


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


WATCHLIST = Watchlist(entries=[
    WatchlistEntry(name="Hanako Yamada", kind="person", category="anime", roles=["voice_actor"], wikipedia="Hanako_Yamada"),
    WatchlistEntry(name="Jujutsu Kaisen", kind="series", category="anime", wikipedia="Jujutsu Kaisen"),
])


def wiki_source(name="Wikipedia", **kw) -> Source:
    return Source(name=name, type="wikipedia", category="celebrity", trust="signal", **kw)


def change(title="Deaths in November 2026", new=1001, old=1000, *, comment="+John Doe", user="Editor1",
           type="edit", namespace=0, wiki="enwiki", bot=False, ts=NOW - 5) -> dict:
    return {
        "$schema": "/mediawiki/recentchange/1.0.0",
        "meta": {"domain": "en.wikipedia.org", "stream": "mediawiki.recentchange"},
        "type": type, "namespace": namespace, "title": title, "comment": comment, "timestamp": ts,
        "user": user, "bot": bot, "minor": False, "length": {"old": 100, "new": 180},
        "revision": {"old": old, "new": new}, "server_url": "https://en.wikipedia.org",
        "server_name": "en.wikipedia.org", "server_script_path": "/w", "wiki": wiki,
    }


class FakeWiki:
    """Wikimedia API + EventStreams double."""

    def __init__(self):
        self.diffs: dict[int, str] = {}
        self.reverted: set[int] = set()
        self.requests: list[httpx.Request] = []
        self.sse_bodies: list[bytes] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert "newsalert" in request.headers["user-agent"]
        if request.url.host == "stream.wikimedia.org":
            return httpx.Response(200, content=self.sse_bodies.pop(0), headers={"content-type": "text/event-stream"})
        p = request.url.params
        if p.get("action") == "compare":
            return httpx.Response(200, json={"compare": {"fromrevid": int(p["fromrev"]), "torevid": int(p["torev"]), "body": self.diffs[int(p["torev"])]}})
        if p.get("action") == "query" and p.get("rvprop") == "ids|tags":
            revs = [int(r) for r in p["revids"].split("|")]
            return httpx.Response(200, json={"query": {"pages": [{"pageid": 1, "title": "X", "revisions": [
                {"revid": r, "parentid": r - 1, "tags": ["mw-reverted"] if r in self.reverted else []} for r in revs
            ]}]}})
        if p.get("action") == "query" and p.get("redirects"):
            titles = p["titles"].split("|")
            return httpx.Response(200, json={"query": {
                "redirects": [{"from": "Hanako Yamada", "to": "Hanako Yamada (voice actress)"}] if "Hanako Yamada" in titles else [],
                "pages": [{"title": t} for t in titles],
            }})
        return httpx.Response(404)

    def calls(self, action):
        return [r for r in self.requests if r.url.params.get("action") == action]


@pytest.fixture
async def wiki(db, settings, pipeline):
    api = FakeWiki()
    clock = Clock()
    async with httpx.AsyncClient(transport=httpx.MockTransport(api.handler), headers={"User-Agent": settings.polling.user_agent}) as client:
        ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings, watchlist=WATCHLIST)
        w = WikipediaWatcher(wiki_source(), ctx, clock=clock)
        yield w, api, clock


# --------------------------------------------------------------------------- parsing


async def test_sse_parser_handles_ids_comments_and_multiline_data():
    async def lines():
        for line in [":ok", "", "event: message", "id: [{\"topic\":\"t\",\"offset\":1}]", 'data: {"a":', "data: 1}", "",
                     "event: message", "data: {\"b\":2}", "", "data: trailing"]:
            yield line

    events = [e async for e in iter_sse(lines())]
    assert [(e.event, e.data, e.id) for e in events] == [
        ("message", '{"a":\n1}', '[{"topic":"t","offset":1}]'),
        ("message", '{"b":2}', '[{"topic":"t","offset":1}]'),
        ("message", "trailing", '[{"topic":"t","offset":1}]'),
    ]


def test_deaths_titles_roll_over_with_month_and_year():
    assert deaths_titles(NOW) == {"Deaths in November 2026", "Deaths in 2026"}
    assert deaths_titles(NOW, previous_month_days=7) == {
        "Deaths in November 2026", "Deaths in 2026", "Deaths in October 2026",
    }
    assert deaths_titles(DEC_1_EARLY) == {"Deaths in December 2026", "Deaths in 2026"}
    jan_3_2027 = 1_798_934_400.0 + 2 * 86400
    assert deaths_titles(jan_3_2027, previous_month_days=7) == {
        "Deaths in January 2027", "Deaths in 2027", "Deaths in December 2026", "Deaths in 2026",
    }
    assert normalize_title("hanako_Yamada ") == "Hanako Yamada"


async def test_title_filter_follows_the_clock(wiki):
    w, _, clock = wiki
    w.cfg = w.cfg.model_copy(update={"deaths_previous_month_days": 0})
    clock.t = NOV_30_LATE
    assert w.classify("Deaths in November 2026", clock.t) == ("deaths", None)
    assert w.classify("Deaths in December 2026", clock.t) is None
    clock.t = DEC_1_EARLY
    assert w.classify("Deaths in November 2026", clock.t) is None
    assert w.classify("Deaths in December 2026", clock.t) == ("deaths", None)
    assert w.classify("Deaths in 2026", clock.t) == ("deaths", None)
    assert w.classify("Hanako Yamada", clock.t)[1].name == "Hanako Yamada"
    assert w.classify("Some Other Page", clock.t) is None


def test_deaths_diff_yields_one_entry_per_newly_added_line():
    rows = parse_diff(DEATHS_DIFF)
    entries = new_death_entries(rows)
    assert [wikitext_to_plain(e) for e in entries] == [
        "John Doe, 78, American actor (Show X).",
        "Hanako Yamada, 64, Japanese voice actress (Spy × Family), cancer.",
    ]  # the age fix for Old Person and the moved Moved Person line are not new


def test_wikitext_to_plain():
    assert wikitext_to_plain("*[[A B|A]], 3, {{ill|Taro Sato|ja}} ''[[Show]]''<ref>{{cite|x}}</ref>{{citation needed}}") == "A, 3, Taro Sato Show"
    assert wikitext_to_plain("[[Category:2026 deaths]]") == ""


def test_watch_signals_person_death_edit():
    signals, snippet = watch_signals(parse_diff(PERSON_DIFF), "person", 2026)
    assert {"death_date", '"is" -> "was"', "deaths category"} <= set(signals)
    assert "death_date" in snippet and "1 November 2026" in snippet


def test_watch_signals_ignore_noise_and_need_recency_for_series():
    filmography = [DiffRow(added="| 2026 || ''[[Death Note]]'' (remake) || Ryuk || Voice")]
    assert watch_signals(filmography, "person", 2026)[0] == []
    plot = [DiffRow(added="In the final arc, Gojo died protecting his students.")]
    assert watch_signals(plot, "series", 2026)[0] == []
    news = [DiffRow(added="In November 2026, a second season was announced.<ref>{{cite web|title=x}}</ref>")]
    assert watch_signals(news, "series", 2026)[0] == ["was announced"]
    old_news = [DiffRow(added="The anime was announced in 2019.")]
    assert watch_signals(old_news, "series", 2026)[0] == []
    arrest = [DiffRow(added="She was arrested in Tokyo on charges of fraud.")]
    assert watch_signals(arrest, "person", 2026)[0] == ["arrested"]


# --------------------------------------------------------------------------- end to end


async def test_deaths_page_edit_becomes_one_item_per_entry(wiki, sink):
    w, api, _ = wiki
    api.diffs[1001] = DEATHS_DIFF
    await w.handle_change(change())
    await w.drain()
    items = [i for _, i in sink.items]
    assert [i.text for i in items] == [
        'Deaths in November 2026: added "John Doe, 78, American actor (Show X)."',
        'Deaths in November 2026: added "Hanako Yamada, 64, Japanese voice actress (Spy × Family), cancer."',
    ]
    assert items[0].url == "https://en.wikipedia.org/w/index.php?diff=1001&oldid=1000"
    assert items[1].url == "https://en.wikipedia.org/w/index.php?diff=1001&oldid=1000&entry=2"
    assert [i.external_id for i in items] == ["enwiki:1001:1", "enwiki:1001:2"]
    assert all(i.trust == "signal" and i.category == "celebrity" and i.source == "Wikipedia" for i in items)
    assert items[0].account == "Editor1" and items[0].published_at == NOW - 5
    assert set(w.pending) == {1001}


async def test_irrelevant_changes_are_ignored_without_api_calls(wiki, sink):
    w, api, _ = wiki
    for c in [
        change(wiki="dewiki"),
        change(namespace=1),
        change(type="log"),
        change(title="Some Random Article"),
        change(title="Hanako Yamada", bot=True),
        change(comment="Reverted edits by [[Special:Contributions/X|X]] to last version by Y"),
    ]:
        await w.handle_change(c)
    await w.drain()
    assert api.requests == [] and sink.items == []


async def test_watchlist_page_emits_only_newsworthy_edits(wiki, sink):
    w, api, _ = wiki
    api.diffs[2001] = PERSON_DIFF
    api.diffs[2002] = '<tr><td colspan="2" class="diff-empty"></td><td class="diff-marker" data-marker="+"></td><td class="diff-addedline"><div>| 2026 || \'\'Some Show\'\' || Lead</div></td></tr>'
    await w.handle_change(change("Hanako Yamada", new=2002, old=2000, comment="filmography"))
    await w.handle_change(change("Hanako Yamada", new=2001, old=2000, comment="died per NHK"))
    await w.drain()
    assert len(sink.items) == 1
    item = sink.items[0][1]
    assert item.category == "anime" and item.trust == "signal" and item.external_id == "enwiki:2001"
    assert item.url == "https://en.wikipedia.org/w/index.php?diff=2001&oldid=2000"
    assert "Hanako Yamada" in item.text and "death_date" in item.text and "died per NHK" in item.text


async def test_redirect_targets_are_watched(wiki):
    w, api, _ = wiki
    await w.resolve_redirects()
    assert w.classify("Hanako Yamada (voice actress)", NOW)[1].name == "Hanako Yamada"
    n = len(api.requests)
    await w.resolve_redirects()  # cached
    assert len(api.requests) == n


# --------------------------------------------------------------------------- reverts


async def _emit_deaths(w, api, revid=1001, user="Vandal"):
    api.diffs[revid] = DEATHS_DIFF
    await w.handle_change(change(new=revid, old=revid - 1, user=user))
    await w.drain()


@pytest.fixture
def retracts(pipeline):
    calls = []
    real = pipeline.retract

    async def spy(source, external_id, reason):
        calls.append((source, external_id, reason))
        return await real(source, external_id, reason)

    pipeline.retract = spy
    return calls


@pytest.mark.parametrize("comment", [
    "Undid revision 1001 by [[Special:Contributions/Vandal|Vandal]] ([[User talk:Vandal|talk]]) unsourced",
    "Reverted edits by [[Special:Contributions/Vandal|Vandal]] ([[User talk:Vandal|talk]]) to last version by Good",
    "Reverted 1 edit by [[Special:Contributions/Vandal|Vandal]] ([[User talk:Vandal|talk]]): Hoax",
    "Restored revision 1000 by [[Special:Contributions/Good|Good]] ([[User talk:Good|talk]])",
])
async def test_revert_summary_within_window_retracts(wiki, retracts, db, comment):
    w, api, clock = wiki
    await _emit_deaths(w, api)
    clock.t += 5 * 60
    await w.handle_change(change(new=1002, old=1001, user="Good", comment=comment))
    assert retracts == [
        ("Wikipedia", "enwiki:1001:1", "wikipedia edit reverted"),
        ("Wikipedia", "enwiki:1001:2", "wikipedia edit reverted"),
    ]
    assert w.pending == {}
    deleted = db.conn.execute("SELECT COUNT(*) FROM items WHERE deleted_at IS NOT NULL").fetchone()[0]
    assert deleted == 2


async def test_unrelated_revert_or_edit_does_not_retract(wiki, retracts):
    w, api, clock = wiki
    await _emit_deaths(w, api)
    await w.handle_change(change(new=1002, old=1001, user="Good", comment="Undid revision 999 by Someone"))
    await w.handle_change(change(new=1003, old=1002, user="Good", comment="copyedit"))
    assert retracts == [] and set(w.pending) == {1001}


async def test_revert_after_window_is_ignored(wiki, retracts):
    w, api, clock = wiki
    await _emit_deaths(w, api)
    clock.t += 16 * 60
    await w.handle_change(change(new=1002, old=1001, user="Good", comment="Undid revision 1001 by Vandal"))
    api.reverted.add(1001)
    await w.check_reverts_once()
    assert retracts == [] and w.pending == {}
    assert w.ctx.db.kv_get("wikipedia:pending") == "[]"


async def test_mw_reverted_tag_retracts_within_window(wiki, retracts):
    w, api, clock = wiki
    await _emit_deaths(w, api)
    clock.t += 60
    await w.check_reverts_once()
    assert retracts == []  # not reverted yet
    api.reverted.add(1001)
    clock.t += 120
    await w.check_reverts_once()
    assert [r[1] for r in retracts] == ["enwiki:1001:1", "enwiki:1001:2"]
    tag_calls = [r for r in api.calls("query") if r.url.params.get("rvprop") == "ids|tags"]
    assert tag_calls[0].url.params["revids"] == "1001"


async def test_pending_reverts_survive_a_restart(wiki, db, settings, pipeline, retracts):
    w, api, clock = wiki
    await _emit_deaths(w, api)
    w2 = WikipediaWatcher(wiki_source(), w.ctx, clock=clock)
    assert set(w2.pending) == {1001}
    clock.t += 60
    await w2.handle_change(change(new=1002, old=1001, comment="Undid revision 1001 by Vandal"))
    assert len(retracts) == 2


# --------------------------------------------------------------------------- stream


def sse(*events) -> bytes:
    out = [":ok\n\n"]
    for i, ev in enumerate(events):
        out.append(f"event: message\nid: [{{\"topic\":\"eqiad.mediawiki.recentchange\",\"partition\":0,\"offset\":{i}}}]\ndata: {json.dumps(ev)}\n\n")
    return "".join(out).encode()


async def test_stream_connects_processes_and_resumes_with_last_event_id(wiki, sink, db):
    w, api, _ = wiki
    api.diffs[1001] = DEATHS_DIFF
    api.sse_bodies = [sse(change(title="Unrelated"), change()), sse()]
    await w.run_once()   # stream ends -> reconnect delay
    await w.drain()
    assert len(sink.items) == 2
    state = db.get_source_state("Wikipedia")
    assert state["seeded"] == 1 and state["last_success_at"] is not None
    await w.run_once()
    streams = [r for r in api.requests if r.url.host == "stream.wikimedia.org"]
    assert "last-event-id" not in streams[0].headers
    assert streams[1].headers["last-event-id"] == '[{"topic":"eqiad.mediawiki.recentchange","partition":0,"offset":1}]'
    assert streams[0].headers["accept"] == "text/event-stream"


async def test_stream_http_error_marks_failing(db, settings, pipeline):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(429, headers={"Retry-After": "30"}))) as client:
        ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings, watchlist=WATCHLIST)
        w = WikipediaWatcher(wiki_source(), ctx)
        delay = await w.run_once()
    assert delay >= 30
    assert db.get_source_state("Wikipedia")["failing_since"] is not None


def test_build_watchers_one_wikipedia_stream(db, settings, pipeline):
    ctx = WatcherContext(db=db, pipeline=pipeline, client=httpx.AsyncClient(), settings=settings, watchlist=WATCHLIST)
    ws = build_watchers([wiki_source(), wiki_source(name="Wikipedia 2")], ctx)
    assert len(ws) == 1 and isinstance(ws[0], WikipediaWatcher) and ws[0].name == "Wikipedia"


def test_real_watchlist_titles_are_loaded(db, settings, pipeline):
    import yaml

    raw = yaml.safe_load((Path(__file__).parent.parent / "config" / "watchlist.yaml").read_text(encoding="utf-8"))
    wl = Watchlist.model_validate(raw)
    ctx = WatcherContext(db=db, pipeline=pipeline, client=httpx.AsyncClient(), settings=settings, watchlist=wl)
    w = WikipediaWatcher(wiki_source(), ctx)
    assert len(w.watch_titles) >= 300
    assert w.classify("Demon Slayer: Kimetsu no Yaiba", NOW)[0] == "watch"


async def test_bulk_edits_are_skipped(wiki, sink):
    w, api, _ = wiki
    lines = "".join(
        f'<tr><td colspan="2" class="diff-empty"></td><td class="diff-marker" data-marker="+"></td>'
        f'<td class="diff-addedline"><div>*[[Person {i}]], {50 + i}, actor.</div></td></tr>'
        for i in range(12)
    )
    api.diffs[3001] = lines
    await w.handle_change(change(new=3001, old=3000, comment="tidy up"))
    await w.drain()
    assert sink.items == [] and w.pending == {}


async def test_run_starts_all_loops_and_cancels_cleanly(db, settings, pipeline, sink):
    import asyncio

    api = FakeWiki()
    api.diffs[1001] = DEATHS_DIFF
    api.sse_bodies = [sse(change())] + [sse()] * 50
    async with httpx.AsyncClient(transport=httpx.MockTransport(api.handler), headers={"User-Agent": settings.polling.user_agent}) as client:
        ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings, watchlist=WATCHLIST)
        w = WikipediaWatcher(wiki_source(), ctx)
        task = asyncio.create_task(w.run())
        for _ in range(100):
            await asyncio.sleep(0.02)
            if len(sink.items) == 2:
                break
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(sink.items) == 2  # stream -> queue -> worker -> pipeline


def test_user_agent_contact_check():
    assert not has_contact("newsalert/0.1 (personal breaking-news alerts; low-frequency polling)")
    assert has_contact("newsalert/0.1 (personal alerts; me@example.com)")
    assert has_contact("newsalert/0.1 (+https://github.com/me/newsalert)")
