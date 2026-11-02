"""End-to-end story behaviour: clustering, confidence, follow-ups, retractions, controls."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from newsalert.alert import DeliveryResult
from newsalert.alert.dispatch import MUTE_KEY, Dispatcher, in_quiet_hours
from newsalert.config import AppConfig, QuietHoursSettings, Settings, Source, Watchlist, WatchlistEntry
from newsalert.confidence import DEATH_WARNING
from newsalert.engine import AlertEngine
from newsalert.health import HealthMonitor
from newsalert.models import RawItem
from newsalert.pipeline import Pipeline
from newsalert.triage import HaikuTriager, TriageResult, fallback_result
from newsalert.watchlist import WatchlistIndex


class FakeTriager:
    """Deterministic triage: rules keyed by a substring of the headline."""

    def __init__(self, rules: dict[str, dict] | None = None, same_event: bool | None = None):
        self.rules = rules or {}
        self.calls = 0
        self.tiebreaks = 0
        self._same = same_event

    async def triage(self, item):
        self.calls += 1
        for key, r in self.rules.items():
            if key.lower() in item.title.lower():
                base = dict(relevant=True, category=item.category, event_type="announcement", subject=key,
                            importance=4, is_rumor=False, summary=f"Summary of {key}.", ai_ok=True)
                base.update(r)
                return TriageResult(**base)
        return TriageResult(relevant=False, category=item.category, event_type="other", subject="?",
                            importance=1, is_rumor=False, summary="irrelevant", ai_ok=True)

    async def same_event(self, a, b):
        self.tiebreaks += 1
        return self._same


class FakeNotifier:
    channel = "fake"

    def __init__(self):
        self.alerts = []

    async def send(self, alert):
        self.alerts.append(alert)
        return DeliveryResult(ok=True, channel=self.channel)


WATCHLIST = Watchlist(entries=[
    WatchlistEntry(name="Attack on Titan", kind="series", category="anime", aliases=["Shingeki no Kyojin", "進撃の巨人"]),
    WatchlistEntry(name="Yuki Kaji", kind="person", category="anime", aliases=["梶裕貴"]),
    WatchlistEntry(name="Friends", kind="series", category="tv", match_risk=True),
])


def src(name, trust, group=None, type_="rss", category="anime"):
    kw = {"url": f"https://{name.replace(' ', '').lower()}.example/feed"} if type_ in ("rss", "youtube") else {"account": name}
    return Source(name=name, type=type_, category=category, trust=trust, group=group, **kw)


class Harness:
    def __init__(self, tmp_path, triager=None, settings: Settings | None = None, clock=None):
        from newsalert.db import Database

        self.settings = settings or Settings()
        self.settings.alerts.normal_min_gap_seconds = 0
        self.db = Database(tmp_path / "t.db")
        self.cfg = AppConfig(root=tmp_path, config_dir=tmp_path, settings=self.settings, sources=[], watchlist=WATCHLIST)
        self.clock = clock or time.time
        self.triager = triager or FakeTriager()
        self.engine = AlertEngine(self.db, self.cfg, self.triager, WatchlistIndex(WATCHLIST), clock=self.clock)
        self.notifier = FakeNotifier()

        async def send(alert):
            return [await self.notifier.send(alert)]

        self.dispatcher = Dispatcher(self.db, self.settings, send=send, build_story_alert=self.engine.build_ring_alert,
                                     clock=self.clock, echo=False)
        self.engine.dispatcher = self.dispatcher
        self.pipeline = Pipeline(self.db, self.settings, self.engine)
        self.n = 0

    async def feed(self, source: Source, title, *, text=None, url=None, age_s=30, ext=None, seeding=False):
        self.n += 1
        now = self.clock()
        item = RawItem.from_source(
            source, account=source.account if source.type in ("x", "bluesky") else None,
            url=url or f"https://{source.name.replace(' ', '').lower()}.example/{self.n}",
            external_id=ext or f"id-{self.n}", title=title, text=text or title,
            published_at=now - age_s, fetched_at=now,
        )
        await self.pipeline.ingest(source, [item], seeding=seeding)
        await self.engine.drain()
        while not self.dispatcher._queue.empty():
            await self.dispatcher.process_one()
        return item

    def rings(self):
        return [a for a in self.notifier.alerts if a.kind == "ring"]

    def kinds(self):
        return [a.kind for a in self.notifier.alerts]


# ------------------------------------------------------------------ clustering


async def test_same_story_from_three_sources_rings_once(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Attack on Titan": {"event_type": "announcement", "importance": 4}}))
    ann, cr, variety = src("ANN", "major", "ann"), src("Crunchyroll", "major", "cr"), src("Variety", "major", "penske")
    await h.feed(ann, "Attack on Titan gets new anime film announced")
    await h.feed(cr, "New Attack on Titan anime film announced for 2027")
    await h.feed(variety, "'Attack on Titan' film announced by studio")
    assert len(h.rings()) == 1
    stories = h.db.conn.execute("SELECT * FROM stories").fetchall()
    assert len(stories) == 1
    assert len(h.db.story_items(stories[0]["id"])) == 3
    assert h.triager.calls == 1  # later items joined by cheap matching, no extra AI calls


async def test_parallel_items_about_same_event_ring_once(tmp_path):
    """Two outlets publish within the same poll; both get triaged concurrently."""
    h = Harness(tmp_path, FakeTriager({"Kaji": {"subject": "Yuki Kaji", "event_type": "health", "importance": 4}}))
    a, b = src("ANN", "major", "ann"), src("Natalie", "major", "natalie")
    now = time.time()
    items = []
    for s, title in ((a, "Voice actor Yuki Kaji takes medical leave"), (b, "梶裕貴 体調不良で休養")):
        items.append((s, RawItem.from_source(s, url=f"https://{s.name}.ex/1", external_id=title, title=title, text=title,
                                              published_at=now - 20, fetched_at=now)))
    await asyncio.gather(*(h.pipeline.ingest(s, [i], seeding=False) for s, i in items))
    await h.engine.drain()
    while not h.dispatcher._queue.empty():
        await h.dispatcher.process_one()
    assert len(h.rings()) == 1


async def test_different_event_same_person_is_new_story(tmp_path):
    h = Harness(tmp_path, FakeTriager({
        "award": {"subject": "Yuki Kaji", "event_type": "award", "importance": 4},
        "hospitalized": {"subject": "Yuki Kaji", "event_type": "health", "importance": 4},
    }))
    ann = src("ANN", "major", "ann")
    await h.feed(ann, "Yuki Kaji wins award at Seiyu Awards")
    await h.feed(ann, "Yuki Kaji hospitalized after collapse")
    assert len(h.rings()) == 2


async def test_ambiguous_match_uses_ai_tiebreak(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Kaji": {"subject": "Yuki Kaji", "event_type": "other", "importance": 4}},
                                      same_event=True))
    ann, nat = src("ANN", "major", "ann"), src("Natalie", "major", "natalie")
    await h.feed(ann, "Yuki Kaji posts message to fans")
    await h.feed(nat, "Statement from Yuki Kaji's agency")
    assert h.triager.tiebreaks >= 1
    assert len(h.rings()) == 1


# ------------------------------------------------------------------ confidence + upgrades


async def test_wikipedia_only_death_is_unconfirmed_with_warning(tmp_path):
    h = Harness(tmp_path, FakeTriager({"John Doe": {"subject": "John Doe", "event_type": "death", "importance": 5,
                                                    "category": "celebrity"}}))
    wiki = src("Wikipedia", "signal", type_="wikipedia", category="celebrity")
    await h.feed(wiki, 'Deaths in November 2026: added "John Doe, 78, American actor"')
    (ring,) = h.rings()
    assert ring.urgency == "urgent"
    assert "[UNCONFIRMED]" in ring.title and "CONFIRMED]" not in ring.title.replace("UNCONFIRMED", "")
    assert DEATH_WARNING in ring.message
    # A second Wikipedia edit (another signal) still never makes it CONFIRMED.
    await h.feed(wiki, 'Deaths in 2026: added "John Doe, 78, American actor"')
    story = h.db.conn.execute("SELECT * FROM stories").fetchone()
    assert story["confidence"] == "UNCONFIRMED"


async def test_later_major_sources_upgrade_quietly(tmp_path):
    h = Harness(tmp_path, FakeTriager({"John Doe": {"subject": "John Doe", "event_type": "death", "importance": 5,
                                                    "category": "celebrity"}}))
    wiki = src("Wikipedia", "signal", type_="wikipedia", category="celebrity")
    await h.feed(wiki, "John Doe dies at 78, Wikipedia updated")
    await h.feed(src("Variety", "major", "penske"), "John Doe, star of Show X, dies at 78")
    await h.feed(src("Deadline", "major", "penske"), "John Doe dead at 78")  # same group: still single outlet
    await h.feed(src("BBC", "major", "bbc"), "Actor John Doe dies aged 78")
    assert h.kinds() == ["ring", "followup", "followup"]
    first_up, second_up = h.notifier.alerts[1], h.notifier.alerts[2]
    assert all(a.urgency == "quiet" for a in (first_up, second_up))
    assert "SINGLE OUTLET" in first_up.title and "CONFIRMED" in second_up.title
    assert "Now confirmed by:" in second_up.message and "BBC" in second_up.message


async def test_retracted_wikipedia_edit_sends_possibly_false(tmp_path):
    h = Harness(tmp_path, FakeTriager({"John Doe": {"subject": "John Doe", "event_type": "death", "importance": 5}}))
    wiki = src("Wikipedia", "signal", type_="wikipedia", category="celebrity")
    await h.feed(wiki, "John Doe dies at 78", ext="rev:123")
    assert await h.pipeline.retract("Wikipedia", "rev:123", "wikipedia edit reverted")
    await h.engine.drain()
    assert h.kinds() == ["ring", "retraction"]
    retraction = h.notifier.alerts[1]
    assert retraction.title.startswith("[POSSIBLY FALSE]")
    assert retraction.urgency == "normal"  # loud enough: it was an urgent story with no other source
    assert "No other sources" in retraction.message
    assert h.db.conn.execute("SELECT status FROM stories").fetchone()["status"] == "retracted"


async def test_retraction_after_window_is_ignored(tmp_path):
    t = [time.time()]
    h = Harness(tmp_path, FakeTriager({"John Doe": {"event_type": "death", "importance": 5}}), clock=lambda: t[0])
    wiki = src("Wikipedia", "signal", type_="wikipedia")
    await h.feed(wiki, "John Doe dies at 78", ext="rev:9")
    t[0] += 16 * 60
    await h.pipeline.retract("Wikipedia", "rev:9", "reverted")
    await h.engine.drain()
    assert h.kinds() == ["ring"]


async def test_rumor_is_labelled(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Season 5": {"is_rumor": True, "importance": 4}}))
    await h.feed(src("Leaks", "signal", category="anime"), "Insider: Season 5 in production")
    assert "UNCONFIRMED · RUMOR" in h.rings()[0].title


# ------------------------------------------------------------------ triage outcomes


async def test_irrelevant_and_low_importance_are_dropped(tmp_path):
    h = Harness(tmp_path, FakeTriager({"merch": {"importance": 2}}))
    await h.feed(src("ANN", "major"), "Top 10 anime openings of the week")  # irrelevant
    await h.feed(src("ANN", "major"), "New merch line for some show")       # importance 2 < 3
    assert h.rings() == []
    statuses = [r["status"] for r in h.db.conn.execute("SELECT status FROM stories")]
    assert statuses == ["dropped", "dropped"]


async def test_watchlist_boost_makes_urgent(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Attack on Titan": {"subject": "Attack on Titan", "importance": 3}}))
    await h.feed(src("ANN", "major"), "Attack on Titan stage play announced")
    (ring,) = h.rings()
    story = h.db.conn.execute("SELECT * FROM stories").fetchone()
    assert story["importance"] == 4 and story["watchlist"] == 1
    assert ring.urgency == "urgent"


async def test_backlog_on_startup_never_alerts(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Titan": {"importance": 5}}))
    ann = src("ANN", "major")
    await h.feed(ann, "Attack on Titan news from this morning", seeding=True)      # first poll: seeded
    await h.feed(ann, "Attack on Titan news from two hours ago", age_s=7200)       # stale backlog
    assert h.notifier.alerts == [] and h.triager.calls == 0


class SlowMessages:
    async def create(self, **kw):
        await asyncio.sleep(10)


async def test_anthropic_timeout_still_alerts_with_raw_headline(tmp_path):
    settings = Settings()
    settings.triage.timeout_seconds = 0.2
    triager = HaikuTriager(settings.triage, client=SimpleNamespace(messages=SlowMessages()))
    h = Harness(tmp_path, triager, settings=settings)
    triager.db = h.db
    t0 = time.monotonic()
    await h.feed(src("TMZ", "major", category="celebrity"), "Famous Singer dies at 61")
    assert time.monotonic() - t0 < 2
    (ring,) = h.rings()
    assert "Famous Singer dies at 61" in ring.title
    assert "no summary" in ring.message
    assert ring.urgency == "urgent"  # keyword fallback still recognises a death
    usage = h.db.conn.execute("SELECT * FROM usage").fetchone()
    assert usage["ok"] == 0 and "timeout" in usage["error"]


# ------------------------------------------------------------------ controls


async def test_quiet_hours_hold_normal_then_digest(tmp_path):
    settings = Settings()
    settings.quiet_hours = QuietHoursSettings(enabled=True, start="00:00", end="23:59", timezone="UTC")
    h = Harness(tmp_path, FakeTriager({
        "Show A": {"importance": 3}, "Show B": {"importance": 3},
        "Star": {"event_type": "death", "importance": 5, "subject": "Star"},
    }), settings=settings)
    await h.feed(src("ANN", "major"), "Show A renewed for season 2")
    await h.feed(src("Variety", "major", "penske"), "Show B gets trailer")
    await h.feed(src("TMZ", "major", "tmz"), "Star dies at 90")
    assert [a.urgency for a in h.notifier.alerts] == ["urgent"]  # urgent still rings
    settings.quiet_hours.enabled = False
    await h.dispatcher.flush_held()
    digest = h.notifier.alerts[-1]
    assert digest.kind == "digest" and "2 stories" in digest.title
    assert "Show A" in digest.message and "Show B" in digest.message


async def test_mute_delivers_silently(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Star": {"event_type": "death", "importance": 5}}))
    h.db.kv_set(MUTE_KEY, str(time.time() + 600))
    await h.feed(src("TMZ", "major"), "Star dies at 90")
    (ring,) = h.rings()
    assert ring.urgency == "quiet" and "muted" in ring.message


async def test_normal_alerts_are_spaced(tmp_path):
    t = [1000.0]
    h = Harness(tmp_path, FakeTriager({"Show One": {"importance": 3}, "Show Two": {"importance": 3}}), clock=lambda: t[0])
    h.settings.alerts.normal_min_gap_seconds = 30
    slept = []

    async def fake_sleep(s):
        slept.append(s)
        t[0] += s

    import newsalert.alert.dispatch as d
    orig = d.asyncio.sleep
    d.asyncio.sleep = fake_sleep
    try:
        await h.feed(src("ANN", "major"), "Show One renewed")
        await h.feed(src("Variety", "major", "penske"), "Show Two trailer released")
    finally:
        d.asyncio.sleep = orig
    assert len(h.rings()) == 2
    assert slept and abs(slept[0] - 30) < 0.01


def test_quiet_hours_window_wraps_midnight():
    q = QuietHoursSettings(enabled=True, start="23:00", end="07:30", timezone="UTC")
    day = 1_793_440_800  # 2026-10-31 10:00 UTC
    assert not in_quiet_hours(q, day)
    assert in_quiet_hours(q, day + 13.5 * 3600)   # 23:30
    assert in_quiet_hours(q, day + 20 * 3600)     # 06:00 next day
    assert not in_quiet_hours(q, day + 22 * 3600)  # 08:00


async def test_health_alert_once_per_failure_episode(tmp_path):
    t = [10_000.0]
    h = Harness(tmp_path, clock=lambda: t[0])
    s = src("TMZ", "major")
    h.cfg.sources.append(s)
    mon = HealthMonitor(h.db, h.cfg, h.dispatcher, clock=lambda: t[0])
    h.db.update_source_state("TMZ", failing_since=t[0], last_error="HTTP 403", consecutive_failures=3)
    t[0] += 9 * 60
    assert await mon.check() == []
    t[0] += 2 * 60
    assert await mon.check() == ["TMZ"]
    assert await mon.check() == []           # no repeat for the same episode
    await h.dispatcher.process_one()
    (alert,) = h.notifier.alerts
    assert alert.kind == "health" and "TMZ" in alert.title and "HTTP 403" in alert.message
    h.db.update_source_state("TMZ", failing_since=None)
    await mon.check()
    h.db.update_source_state("TMZ", failing_since=t[0])
    t[0] += 11 * 60
    assert await mon.check() == ["TMZ"]      # new episode alerts again


async def test_alert_format_matches_spec(tmp_path):
    h = Harness(tmp_path, FakeTriager({"Season 2": {"subject": "Y", "importance": 4}}))
    x = Source(name="Studio X (X)", type="x", account="StudioX_official", category="anime", trust="official")
    await h.feed(x, "Studio X announces Season 2 of Y", url="https://x.com/StudioX_official/status/1", age_s=47)
    await h.feed(src("ANN", "major", "ann"), "Studio X announces Season 2 of Y anime", url="https://ann.example/y2")
    ring = h.rings()[0]
    assert ring.title == "[ANIME] [OFFICIAL SOURCE] Studio X announces Season 2 of Y"
    lines = ring.message.splitlines()
    assert lines[0] == "Summary: Summary of Season 2."
    assert lines[1].startswith("Source: @StudioX_official (X) · 4") and lines[1].endswith("s ago")
    assert ring.click_url == "https://x.com/StudioX_official/status/1"


def test_fallback_result_uses_keywords():
    from newsalert.triage import TriageInput

    r = fallback_result(TriageInput(source="s", trust="major", category="tv", title="Show X cancelled after one season",
                                    text=""), "timeout")
    assert r.event_type == "cancellation" and r.summary is None and not r.ai_ok


async def test_retraction_while_ring_in_flight_still_sends_possibly_false(tmp_path):
    h = Harness(tmp_path, FakeTriager({"John Doe": {"event_type": "death", "importance": 5}}))
    release = asyncio.Event()
    real_send = h.notifier.send

    async def slow_send(alert):
        if alert.kind == "ring":
            await release.wait()
        return await real_send(alert)

    h.notifier.send = slow_send
    wiki = src("Wikipedia", "signal", type_="wikipedia")
    feed = asyncio.create_task(h.feed(wiki, "John Doe dies at 78", ext="rev:7"))
    await asyncio.sleep(0.05)                      # ring is now mid-send
    assert h.db.conn.execute("SELECT status FROM stories").fetchone()["status"] == "sending"
    await h.pipeline.retract("Wikipedia", "rev:7", "wikipedia edit reverted")
    release.set()
    await feed
    await h.engine.drain()
    assert sorted(h.kinds()) == ["retraction", "ring"]
    assert h.db.conn.execute("SELECT status FROM stories").fetchone()["status"] == "retracted"


async def test_deaths_page_edit_counts_as_death_without_ai(tmp_path):
    from newsalert.triage import NoAITriager

    h = Harness(tmp_path, NoAITriager())
    await h.feed(src("Wikipedia", "signal", type_="wikipedia", category="celebrity"),
                 'Deaths in November 2026: added "Jane Example, 81, British actress."')
    (ring,) = h.rings()
    assert ring.urgency == "urgent" and DEATH_WARNING in ring.message and "[UNCONFIRMED]" in ring.title
