"""YouTube channel feeds: URL building, Atom parsing, seeding and conditional GET."""

import time
from pathlib import Path

import httpx
import pytest
import yaml

from newsalert.config import Settings, Source, YouTubeSettings
from newsalert.watchers import YouTubeWatcher, build_watchers
from newsalert.watchers.base import WatcherContext
from newsalert.watchers.rss import parse_feed
from newsalert.watchers.youtube import feed_source, feed_url, interval_for, is_channel_id

from conftest import mock_client

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = Path(__file__).parent.parent / "config"
CHANNEL = "UCjfAEJZdfbIjVHdo5yODfyQ"


def yt_source(**kw) -> Source:
    base = dict(name="MAPPA (YouTube)", type="youtube", account=CHANNEL, category="anime", trust="official")
    base.update(kw)
    return Source(**base)


def test_feed_url_from_channel_id_or_url():
    s = Settings()
    assert feed_url(yt_source(), s) == f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"
    custom = "https://www.youtube.com/feeds/videos.xml?playlist_id=UULFjfAEJZdfbIjVHdo5yODfyQ"
    assert feed_url(yt_source(account=None, url=custom), s) == custom
    assert is_channel_id(CHANNEL) and not is_channel_id("@MAPPACHANNEL")
    with pytest.raises(ValueError, match="not a YouTube channel id"):
        feed_url(yt_source(account="@MAPPACHANNEL"), s)


def test_interval_defaults_to_youtube_setting():
    s = Settings()
    assert interval_for(yt_source(), s) == s.youtube.interval
    assert interval_for(yt_source(interval=600), s) == 600
    assert interval_for(yt_source(interval=5), s) == s.polling.min_interval


def test_parse_youtube_feed_fixture():
    src = feed_source(yt_source(), Settings())
    items = parse_feed((FIXTURES / "youtube_channel.xml").read_bytes(), src, fetched_at=time.time())
    assert [i.external_id for i in items] == ["yt:video:NEWVIDEO01", "yt:video:OLDVIDEO02"]
    new = items[0]
    assert new.url == "https://www.youtube.com/watch?v=NEWVIDEO01"
    assert new.title.startswith("TVアニメ「呪術廻戦」第3期 本PV")
    assert "Premieres January 2027 & streaming worldwide." in new.text
    assert new.published_at == 1793588400.0  # 2026-11-02T03:00:00Z
    assert new.source == "MAPPA (YouTube)" and new.source_type == "youtube"
    assert new.trust == "official" and new.category == "anime"
    assert new.account == "MAPPA CHANNEL"


async def test_watcher_seeds_then_alerts_with_conditional_get(db, settings, pipeline, sink):
    body = (FIXTURES / "youtube_channel.xml").read_bytes()
    just_now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - 60)).encode()
    fresh_entry = (
        body.replace(b"NEWVIDEO01", b"FRESHVID03")
        .replace(b"Season 3 Main Trailer", b"Season 4 Announcement")
        .replace(b"Premieres January 2027", b"Season 4 confirmed")
        .replace(b"2026-11-02T03:00:00+00:00", just_now)
    )
    responses = [body, fresh_entry]
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), request.headers.get("if-none-match")))
        return httpx.Response(200, content=responses[len(seen) - 1], headers={"ETag": f'"e{len(seen)}"'})

    async with mock_client(handler) as client:
        ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=settings)
        w = YouTubeWatcher(yt_source(), ctx, interval=120)
        await w.run_once()
        assert sink.items == []  # first poll seeds silently
        await w.run_once()

    assert seen[0] == (f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}", None)
    assert seen[1][1] == '"e1"'
    assert [i.external_id for _, i in sink.items] == ["yt:video:FRESHVID03"]
    state = db.get_source_state("MAPPA (YouTube)")
    assert state["seeded"] == 1 and state["failing_since"] is None


def test_build_watchers_skips_bad_youtube_source(db, settings, pipeline):
    ctx = WatcherContext(db=db, pipeline=pipeline, client=httpx.AsyncClient(), settings=settings)
    ws = build_watchers([yt_source(), yt_source(name="Bad", account="@handle")], ctx)
    assert [w.name for w in ws] == ["MAPPA (YouTube)"]


def test_seeded_sources_yaml_youtube_entries_are_valid():
    raw = yaml.safe_load((CONFIG / "sources.yaml").read_text(encoding="utf-8"))
    yt = [Source.model_validate(r) for r in raw if r.get("type") == "youtube"]
    assert len(yt) >= 15
    for s in yt:
        if s.enabled:  # every enabled channel must have a well-formed id
            assert s.url or is_channel_id(s.account), s.name
        assert s.trust == "official"


def test_settings_yaml_sections_match_models():
    raw = yaml.safe_load((CONFIG / "settings.yaml").read_text(encoding="utf-8")) or {}
    YouTubeSettings.model_validate(raw.get("youtube") or {})
    from newsalert.config import BlueskySettings, WikipediaSettings, XSettings

    BlueskySettings.model_validate(raw.get("bluesky") or {})
    XSettings.model_validate(raw.get("x") or {})
    WikipediaSettings.model_validate(raw.get("wikipedia") or {})
