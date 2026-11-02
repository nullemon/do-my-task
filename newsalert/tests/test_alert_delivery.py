"""Tests for alert delivery: ntfy publishing, local notifications, channel selection."""

from __future__ import annotations

import asyncio
import json
import logging
import stat
import sys
import time
from pathlib import Path

import httpx
import pytest

from newsalert.alert import Alert, DeliveryResult
from newsalert.alert.delivery import build_notifiers, deliver, make_test_alert
from newsalert.alert.local import LocalNotifier, listener_message
from newsalert.alert.ntfy import MAX_MESSAGE_BYTES, NtfyNotifier, ntfy_payload
from newsalert.config import AppConfig, Settings, Watchlist

TOKEN = "tk_testtoken_0123456789abcdef"


def urgent_alert(**kw) -> Alert:
    base = dict(
        kind="ring",
        urgency="urgent",
        title="[ANIME] [OFFICIAL SOURCE] Studio X announces Season 2 of Y",
        message="Summary: s\nSource: @StudioX_official (X) · 47s ago\nLinks: original post · A · B",
        click_url="https://x.com/StudioX_official/status/1",
        links=[(f"Source {i}", f"https://example.com/{i}") for i in range(5)],
        tags=["anime", "announcement"],
        story_id=42,
    )
    base.update(kw)
    return Alert(**base)


class Recorder:
    """httpx.MockTransport handler that replays scripted responses."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        r = self.responses.pop(0) if self.responses else 200
        if isinstance(r, Exception):
            raise r
        if isinstance(r, httpx.Response):
            return r
        return httpx.Response(r, json={"id": "abc", "event": "message"} if r == 200 else {"error": "nope", "http": r})


class FakeSleep:
    def __init__(self):
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def notifier(rec: Recorder, token: str | None = None, sleep=None, **kw) -> NtfyNotifier:
    client = httpx.AsyncClient(transport=httpx.MockTransport(rec))
    return NtfyNotifier(client, topic="na_test_topic_x7k2", url="https://ntfy.example/", token=token,
                        sleep=sleep or FakeSleep(), **kw)


# --------------------------------------------------------------------------- payload


async def test_payload_shape_urgent():
    rec = Recorder(200)
    result = await notifier(rec).send(urgent_alert())
    assert result == DeliveryResult(ok=True, channel="ntfy", attempts=1)

    req = rec.requests[0]
    assert req.method == "POST" and str(req.url) == "https://ntfy.example/"   # JSON publish to the root
    assert req.headers["content-type"] == "application/json"
    body = json.loads(req.content)
    assert set(body) == {"topic", "title", "message", "priority", "tags", "click", "actions"}
    assert body["topic"] == "na_test_topic_x7k2"
    assert body["title"].startswith("[ANIME] [OFFICIAL SOURCE]")
    assert body["message"].startswith("Summary: s\nSource:")
    assert body["priority"] == 5
    assert body["tags"][0] == "rotating_light"
    assert "anime" in body["tags"] and "announcement" in body["tags"] and "na-ring" in body["tags"]
    assert body["click"] == "https://x.com/StudioX_official/status/1"
    assert len(body["actions"]) == 3
    assert body["actions"][0] == {"action": "view", "label": "Source 0", "url": "https://example.com/0", "clear": False}


async def test_payload_normal_and_quiet():
    normal = ntfy_payload(urgent_alert(urgency="normal", kind="retraction", tags=["warning"]), "t")
    assert normal["priority"] == 4
    assert "rotating_light" not in normal["tags"] and normal["tags"] == ["warning", "na-retraction"]

    quiet = ntfy_payload(Alert(kind="followup", urgency="quiet", title="T", message="", click_url=None,
                               tags=["followup", "a,b"]), "t")
    assert quiet["priority"] == 2
    assert quiet["tags"] == ["followup", "a b", "na-followup"]     # commas would split a tag
    assert "click" not in quiet and quiet["actions"] == []
    assert quiet["message"] == "T"                                # ntfy needs a non-empty body


@pytest.mark.parametrize("kind", ["ring", "followup", "retraction", "health", "test", "digest"])
def test_every_kind_gets_a_listener_tag(kind):
    assert f"na-{kind}" in ntfy_payload(urgent_alert(kind=kind), "t")["tags"]


def test_payload_limits():
    long = urgent_alert(message="é" * 5000, title="x" * 400, links=[("L" * 80, "https://e.com"), ("bad", "javascript:x")],
                        click_url="file:///etc/passwd")
    p = ntfy_payload(long, "t")
    assert len(p["message"].encode()) <= MAX_MESSAGE_BYTES
    assert len(p["title"]) <= 250
    assert [a["url"] for a in p["actions"]] == ["https://e.com"]      # non-web links dropped
    assert len(p["actions"][0]["label"]) <= 40
    assert "click" not in p


# --------------------------------------------------------------------------- auth


async def test_auth_header_only_when_token_set():
    rec = Recorder(200, 200)
    await notifier(rec, token=TOKEN).send(urgent_alert())
    await notifier(rec, token=None).send(urgent_alert())
    assert rec.requests[0].headers["authorization"] == f"Bearer {TOKEN}"
    assert "authorization" not in rec.requests[1].headers
    assert TOKEN not in rec.requests[0].content.decode()


# --------------------------------------------------------------------------- retries


async def test_retries_then_success():
    rec = Recorder(503, httpx.ConnectError("refused"), 200)
    sleep = FakeSleep()
    result = await notifier(rec, sleep=sleep).send(urgent_alert())
    assert result.ok and result.attempts == 3
    assert len(rec.requests) == 3
    assert len(sleep.calls) == 2 and sum(sleep.calls) < 5


async def test_retries_exhausted_logs_error(caplog, monkeypatch):
    monkeypatch.setenv("NTFY_TOKEN", TOKEN)
    rec = Recorder(500, httpx.ReadTimeout("slow"), 502, 200)
    with caplog.at_level(logging.WARNING, logger="newsalert.alert.ntfy"):
        result = await notifier(rec, token=TOKEN).send(urgent_alert())
    assert not result.ok and result.attempts == 3 and result.channel == "ntfy"
    assert "502" in result.error
    assert len(rec.requests) == 3                     # 2 extra attempts, not more
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert [r.getMessage() for r in errors] == ["alert.delivery_failed"]
    assert errors[0].attempts == 3 and errors[0].story_id == 42
    for r in caplog.records:                          # token never passed into log records
        assert TOKEN not in json.dumps(r.__dict__, default=str)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413])
async def test_client_errors_not_retried(status, caplog):
    rec = Recorder(status, 200)
    with caplog.at_level(logging.ERROR, logger="newsalert.alert.ntfy"):
        result = await notifier(rec).send(urgent_alert())
    assert not result.ok and result.attempts == 1 and len(rec.requests) == 1
    assert str(status) in result.error
    assert any(r.getMessage() == "alert.delivery_failed" for r in caplog.records)


async def test_429_is_retried_and_honours_retry_after():
    rec = Recorder(httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "limit"}), 200)
    sleep = FakeSleep()
    result = await notifier(rec, sleep=sleep).send(urgent_alert())
    assert result.ok and result.attempts == 2
    assert sleep.calls == [2.0]


async def test_429_retry_after_beyond_window_gives_up():
    rec = Recorder(httpx.Response(429, headers={"Retry-After": "60"}), 200)
    result = await notifier(rec).send(urgent_alert())
    assert not result.ok and result.attempts == 1


async def test_retry_settings_are_honoured():
    rec = Recorder(503, 503, 200)
    result = await notifier(rec, retries=0).send(urgent_alert())
    assert not result.ok and result.attempts == 1

    rec = Recorder(503, 503, 200)
    result = await notifier(rec, retry_window=0.6).send(urgent_alert())   # no room for a 0.5 s pause + attempt
    assert not result.ok and result.attempts == 1


async def test_whole_retry_sequence_fits_in_window():
    """Real sleeps: 3 failing attempts finish inside ntfy_retry_window_seconds."""
    rec = Recorder(503, 503, 503)
    client = httpx.AsyncClient(transport=httpx.MockTransport(rec))
    n = NtfyNotifier(client, topic="t", retries=2, retry_window=5.0)
    t0 = time.monotonic()
    result = await n.send(urgent_alert())
    assert result.attempts == 3 and time.monotonic() - t0 < 5.0


async def test_unexpected_exception_does_not_raise():
    rec = Recorder(ValueError("weird"))
    result = await notifier(rec).send(urgent_alert())
    assert not result.ok and result.attempts == 1 and "weird" in result.error


# --------------------------------------------------------------------------- build_notifiers


@pytest.fixture
def cfg(tmp_path) -> AppConfig:
    return AppConfig(root=tmp_path, config_dir=tmp_path / "config", settings=Settings(), sources=[], watchlist=Watchlist())


@pytest.fixture
def client():
    return httpx.AsyncClient(transport=httpx.MockTransport(Recorder()))


@pytest.fixture
def env(monkeypatch):
    for var in ("ALERT_MODE", "NTFY_URL", "NTFY_TOPIC", "NTFY_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.mark.parametrize(
    "mode,topic,expected",
    [
        (None, "na_long_random_topic_123", ["ntfy"]),
        ("ntfy", "na_long_random_topic_123", ["ntfy"]),
        ("NTFY ", "na_long_random_topic_123", ["ntfy"]),
        ("local", "na_long_random_topic_123", ["local"]),
        ("both", "na_long_random_topic_123", ["ntfy", "local"]),
        ("ntfy", "", ["local"]),        # no topic: fall back to local
        ("both", "", ["local"]),
        (None, "", ["local"]),
        ("ntfy", "https://ntfy.sh/bad topic", ["local"]),
        ("weird", "na_long_random_topic_123", ["ntfy"]),
    ],
)
def test_build_notifiers_modes(cfg, client, env, mode, topic, expected):
    if mode is not None:
        env.setenv("ALERT_MODE", mode)
    env.setenv("NTFY_TOPIC", topic)
    assert [n.channel for n in build_notifiers(cfg, client)] == expected


def test_build_notifiers_missing_topic_logs_what_to_set(cfg, client, env, caplog):
    env.setenv("ALERT_MODE", "ntfy")
    with caplog.at_level(logging.ERROR):
        notifiers = build_notifiers(cfg, client)
    assert isinstance(notifiers[0], LocalNotifier)
    rec = next(r for r in caplog.records if r.getMessage() == "alert.ntfy_not_configured")
    assert "NTFY_TOPIC" in rec.hint and ".env" in rec.hint


async def test_build_notifiers_ntfy_uses_env_and_settings(cfg, env):
    env.setenv("NTFY_TOPIC", "na_long_random_topic_123")
    env.setenv("NTFY_URL", "https://ntfy.example")
    env.setenv("NTFY_TOKEN", TOKEN)
    cfg.settings.alerts.ntfy_retries = 0
    rec = Recorder(503, 200)
    (n,) = build_notifiers(cfg, httpx.AsyncClient(transport=httpx.MockTransport(rec)))
    result = await n.send(urgent_alert())
    assert not result.ok and result.attempts == 1         # ntfy_retries honoured
    assert str(rec.requests[0].url) == "https://ntfy.example/"
    assert rec.requests[0].headers["authorization"] == f"Bearer {TOKEN}"
    assert json.loads(rec.requests[0].content)["topic"] == "na_long_random_topic_123"


def test_local_notifier_from_config_paths(cfg):
    n = LocalNotifier.from_config(cfg)
    assert n.ring_sound == cfg.root / "config/sounds/ring.wav"
    assert n.chime_sound == cfg.root / "config/sounds/chime.wav"
    assert n.listener_script == cfg.root / "laptop" / "newsalert_listener.py"


def test_repo_ships_sounds_and_listener():
    root = Path(__file__).resolve().parent.parent
    import wave
    for name, (lo, hi) in {"ring.wav": (1.5, 2.5), "chime.wav": (0.5, 1.2)}.items():
        path = root / "config" / "sounds" / name
        assert path.stat().st_size < 400_000
        with wave.open(str(path)) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 44100)
            assert lo <= w.getnframes() / w.getframerate() <= hi
    assert (root / "laptop" / "newsalert_listener.py").exists()


# --------------------------------------------------------------------------- deliver


class SlowNotifier:
    def __init__(self, channel, ok=True, delay=0.2, exc=None):
        self.channel, self.ok, self.delay, self.exc = channel, ok, delay, exc

    async def send(self, alert):
        await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return DeliveryResult(ok=self.ok, channel=self.channel, error=None if self.ok else "down")


async def test_deliver_runs_channels_concurrently():
    t0 = time.monotonic()
    results = await deliver([SlowNotifier("ntfy"), SlowNotifier("local")], make_test_alert(True))
    assert time.monotonic() - t0 < 0.35
    assert [(r.channel, r.ok) for r in results] == [("ntfy", True), ("local", True)]


async def test_deliver_turns_exceptions_into_results(caplog):
    with caplog.at_level(logging.ERROR):
        results = await deliver([SlowNotifier("ntfy", exc=RuntimeError("boom"), delay=0),
                                 SlowNotifier("local", ok=False, delay=0)], make_test_alert(False))
    assert [(r.channel, r.ok) for r in results] == [("ntfy", False), ("local", False)]
    assert "boom" in results[0].error
    assert any(r.getMessage() == "alert.all_channels_failed" for r in caplog.records)


async def test_deliver_with_no_channels(caplog):
    with caplog.at_level(logging.ERROR):
        assert await deliver([], make_test_alert(True)) == []
    assert any(r.getMessage() == "alert.no_channels" for r in caplog.records)


# --------------------------------------------------------------------------- make_test_alert


@pytest.mark.parametrize("urgent,priority", [(True, 5), (False, 4)])
def test_make_test_alert(urgent, priority):
    a = make_test_alert(urgent)
    assert a.kind == "test" and a.urgency == ("urgent" if urgent else "normal")
    assert a.title == "[ANIME] [OFFICIAL SOURCE] TEST — Studio X announces Season 2 of Y"
    lines = a.message.splitlines()
    assert lines[0].startswith("Summary: ") and "TEST" in lines[0]
    assert lines[1] == "Source: @StudioX_official (X) · 47s ago"
    assert lines[2].startswith("Links: ")
    assert a.click_url and 1 <= len(a.links) <= 3
    p = ntfy_payload(a, "t")
    assert p["priority"] == priority and "na-test" in p["tags"]
    assert ("rotating_light" in p["tags"]) == urgent


# --------------------------------------------------------------------------- LocalNotifier (fake tools)


def _tool(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def fake_bin(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "calls.log"
    monkeypatch.setenv("PATH", str(bin_dir))
    return bin_dir, log_file


@pytest.fixture
def sounds(tmp_path):
    ring, chime = tmp_path / "ring.wav", tmp_path / "chime.wav"
    ring.write_bytes(b"RIFF")
    chime.write_bytes(b"RIFF")
    return ring, chime


async def _wait_for(pred, timeout=3.0):
    t0 = time.monotonic()
    while not pred():
        if time.monotonic() - t0 > timeout:
            return False
        await asyncio.sleep(0.05)
    return True


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell fakes")
async def test_local_linux_normal_and_quiet(fake_bin, sounds):
    bin_dir, calls = fake_bin
    _tool(bin_dir, "notify-send", f'echo "notify $*" >> "{calls}"')
    _tool(bin_dir, "aplay", f'echo "aplay $*" >> "{calls}"')
    n = LocalNotifier(*sounds, platform="linux")

    r = await n.send(make_test_alert(False))
    assert r.ok and r.channel == "local"
    assert await _wait_for(lambda: calls.exists() and "aplay" in calls.read_text())
    text = calls.read_text()
    assert "-u normal" in text and "TEST — Studio X" in text and str(sounds[1]) in text

    calls.unlink()
    r = await n.send(Alert(kind="followup", urgency="quiet", title="quiet one", message="m"))
    assert r.ok
    await asyncio.sleep(0.2)
    text = calls.read_text()
    assert "-u low" in text and "aplay" not in text
    await n.aclose()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell fakes")
async def test_local_linux_urgent_rings_until_dismissed(fake_bin, sounds):
    bin_dir, calls = fake_bin
    # notify-send with --wait: stays "on screen" for 0.8 s, then the owner clicks Dismiss.
    _tool(bin_dir, "notify-send", f'echo "notify $*" >> "{calls}"; sleep 0.8; echo dismiss')
    _tool(bin_dir, "aplay", f'echo "aplay $*" >> "{calls}"; sleep 0.1')
    n = LocalNotifier(*sounds, platform="linux", ring_max_seconds=10)
    r = await n.send(urgent_alert())
    assert r.ok and n.ringing
    assert await _wait_for(lambda: not n.ringing, timeout=5)
    text = calls.read_text()
    assert "--wait" in text and "-u critical" in text
    assert text.count(f"aplay -q {sounds[0]}") >= 2          # looped
    await n.aclose()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell fakes")
async def test_local_ring_stops_at_time_limit(fake_bin, sounds):
    bin_dir, calls = fake_bin
    _tool(bin_dir, "notify-send", "exit 1")                  # no notification daemon
    _tool(bin_dir, "aplay", "sleep 0.1")
    n = LocalNotifier(*sounds, platform="linux", ring_max_seconds=0.5)
    r = await n.send(urgent_alert())
    assert r.ok and n.ringing                                # sound worked even if the popup didn't
    await asyncio.wait_for(n.wait_idle(), 3)                 # what `newsalert test-alert` waits on
    assert not n.ringing
    await n.aclose()


async def test_local_missing_tools_warns_and_does_not_crash(fake_bin, sounds, caplog):
    n = LocalNotifier(*sounds, platform="linux")
    with caplog.at_level(logging.WARNING, logger="newsalert.alert.local"):
        r = await n.send(urgent_alert())
        r2 = await n.send(make_test_alert(False))
    assert not r.ok and not r2.ok and "no notification tool" in r.error
    missing = [r for r in caplog.records if r.getMessage() == "local.tool_missing"]
    assert {m.tool for m in missing} == {"notify-send", "paplay/aplay"}    # each warned once
    await n.aclose()


async def test_local_windows_feeds_listener_child_over_stdin(tmp_path, sounds):
    """platform=win32 path, with a fake listener script standing in for laptop/newsalert_listener.py."""
    out = tmp_path / "child.jsonl"
    args_file = tmp_path / "args.json"
    script = tmp_path / "fake_listener.py"
    script.write_text(
        "import json, sys\n"
        f"json.dump(sys.argv[1:], open({str(args_file)!r}, 'w'))\n"
        "for line in sys.stdin.buffer:\n"
        f"    open({str(out)!r}, 'ab').write(line)\n"
    )
    n = LocalNotifier(*sounds, platform="win32", listener_script=script, listener_log=tmp_path / "l.log")
    assert (await n.send(urgent_alert())).ok
    assert (await n.send(make_test_alert(False))).ok
    assert await _wait_for(lambda: out.exists() and len(out.read_text().splitlines()) == 2)
    first, second = (json.loads(line) for line in out.read_text().splitlines())
    assert first["event"] == "message" and first["priority"] == 5 and "na-ring" in first["tags"]
    assert first["id"] != second["id"] and second["priority"] == 4
    args = json.loads(args_file.read_text())
    assert args[:1] == ["--stdin"] and str(sounds[0]) in args and str(sounds[1]) in args
    await n.aclose()


def test_listener_message_matches_listener_classification():
    import importlib.util
    path = Path(__file__).resolve().parent.parent / "laptop" / "newsalert_listener.py"
    mod = sys.modules.get("newsalert_listener")
    if mod is None:
        spec = importlib.util.spec_from_file_location("newsalert_listener", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["newsalert_listener"] = mod      # dataclasses need the module registered
        spec.loader.exec_module(mod)
    for urgency, level in (("urgent", "urgent"), ("normal", "normal"), ("quiet", "quiet")):
        for kind in ("ring", "followup", "retraction", "health", "test", "digest"):
            m = listener_message(urgent_alert(urgency=urgency, kind=kind), "id1")
            assert mod.classify(m) == level
            assert mod.kind_of(m) == kind
