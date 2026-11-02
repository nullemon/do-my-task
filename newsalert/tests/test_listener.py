"""Tests for laptop/newsalert_listener.py (standalone, stdlib-only script)."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import sys
import threading
import time
import types
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

LISTENER_PATH = Path(__file__).resolve().parent.parent / "laptop" / "newsalert_listener.py"


def _load():
    spec = importlib.util.spec_from_file_location("newsalert_listener", LISTENER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["newsalert_listener"] = mod
    spec.loader.exec_module(mod)
    return mod


L = _load()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("NTFY_URL", "NTFY_TOPIC", "NTFY_TOKEN", "NEWSALERT_SOUNDS_DIR"):
        monkeypatch.delenv(var, raising=False)


def msg(priority=None, event="message", **kw):
    m = {"id": kw.pop("id", "abc123"), "time": kw.pop("time", int(time.time())), "event": event, "topic": "t"}
    if priority is not None:
        m["priority"] = priority
    m.update(kw)
    return m


# --------------------------------------------------------------------------- the file itself


def test_listener_is_stdlib_only_and_standalone():
    src = LISTENER_PATH.read_text(encoding="utf-8")
    assert "import newsalert" not in src and "from newsalert" not in src
    allowed_third_party = set()
    for line in src.splitlines():
        s = line.strip()
        if s.startswith(("import ", "from ")) and not line.startswith((" ", "\t")):
            name = s.split()[1].split(".")[0]
            if name != "__future__":
                assert name in sys.stdlib_module_names or name in allowed_third_party, name


# --------------------------------------------------------------------------- classify


@pytest.mark.parametrize(
    "priority,expected",
    [(5, "urgent"), (4, "normal"), (3, "quiet"), (2, "quiet"), (1, "quiet"), (None, "quiet"),
     ("5", "urgent"), ("max", "urgent"), ("urgent", "urgent"), ("high", "normal"), ("low", "quiet"),
     ("bogus", "quiet"), (9, "urgent"), (0, "quiet"), (True, "quiet")],
)
def test_classify_by_priority(priority, expected):
    assert L.classify(msg(priority)) == expected


@pytest.mark.parametrize("event", ["open", "keepalive", "poll_request", "message_delete", "message_clear", None])
def test_classify_ignores_non_message_events(event):
    m = msg(5, event=event)
    if event is None:
        del m["event"]
    assert L.classify(m) is None


@pytest.mark.parametrize("value", [None, "text", 5, ["event", "message"]])
def test_classify_non_dict(value):
    assert L.classify(value) is None


@pytest.mark.parametrize(
    "tags,priority,expected_level,expected_kind",
    [
        (["rotating_light", "anime", "na-ring"], 5, "urgent", "ring"),
        (["na-ring"], 4, "normal", "ring"),
        (["followup", "white_check_mark", "na-followup"], 2, "quiet", "followup"),
        (["warning", "na-retraction"], 4, "normal", "retraction"),
        (["na-health"], 4, "normal", "health"),
        (["test_tube", "na-test"], 5, "urgent", "test"),
        (["na-digest"], 4, "normal", "digest"),
        (["na-ring"], 2, "quiet", "ring"),        # tags never override priority
        (["na-unknown"], 3, "quiet", None),
        ([], 5, "urgent", None),                  # foreign message (curl, phone): priority still rules
        ("rotating_light,na-test", 5, "urgent", "test"),
    ],
)
def test_classify_and_kind_from_tags(tags, priority, expected_level, expected_kind):
    m = msg(priority, tags=tags)
    assert L.classify(m) == expected_level
    assert L.kind_of(m) == expected_kind


def test_effective_level_downgrades_stale_alerts():
    now = 1_800_000_000
    old = msg(5, time=now - 3600)
    fresh = msg(5, time=now - 30)
    assert L.effective_level(old, now=now, max_age_seconds=900) == "quiet"
    assert L.effective_level(msg(4, time=now - 3600), now=now, max_age_seconds=900) == "quiet"
    assert L.effective_level(fresh, now=now, max_age_seconds=900) == "urgent"
    assert L.effective_level(old, now=now, max_age_seconds=0) == "urgent"     # 0 = always ring
    assert L.effective_level(msg(5, event="keepalive"), now=now) is None


# --------------------------------------------------------------------------- parsing helpers


def test_parse_line():
    assert L.parse_line(b'{"id":"x","event":"keepalive","time":1}\n') == {"id": "x", "event": "keepalive", "time": 1}
    assert L.parse_line('{"event":"open"}') == {"event": "open"}
    assert L.parse_line(b"\n") is None
    assert L.parse_line(b"   ") is None
    assert L.parse_line(b"not json") is None
    assert L.parse_line(b"[1,2]") is None
    assert L.parse_line("{\"title\":\"caf\\u00e9 \u2014 ok\"}".encode()) == {"title": "café — ok"}


def test_links_only_http_and_click_fallback():
    m = msg(5, click="javascript:alert(1)", actions=[
        {"action": "view", "label": "File", "url": "file:///C:/Windows"},
        {"action": "http", "label": "Post", "url": "https://example.com/post"},
        {"action": "view", "label": "ANN", "url": "https://example.com/ann"},
    ])
    assert L.view_links(m) == [("ANN", "https://example.com/ann")]
    assert L.click_url(m) == "https://example.com/ann"
    assert L.click_url(msg(5, click="https://example.com/x")) == "https://example.com/x"
    assert L.click_url(msg(5)) is None


def test_subscribe_url_and_topic_helpers():
    assert L.subscribe_url("https://ntfy.sh/", "my_topic-1") == "https://ntfy.sh/my_topic-1/json"
    assert L.subscribe_url("https://ntfy.sh", "t", "abc") == "https://ntfy.sh/t/json?since=abc"
    assert L.normalize_topic("https://ntfy.sh", " https://ntfy.example/abc_DEF ") == ("https://ntfy.example", "abc_DEF")
    assert L.normalize_topic("https://ntfy.sh", "abc/") == ("https://ntfy.sh", "abc")
    assert L.valid_topic("na_" + "x" * 30)
    assert not L.valid_topic("has space") and not L.valid_topic("") and not L.valid_topic("x" * 65)
    assert not L.valid_topic("tópico")


# --------------------------------------------------------------------------- config


def _args(argv):
    return L.build_parser().parse_args(argv)


def test_config_precedence_ini_env_cli(tmp_path, monkeypatch):
    ini = tmp_path / "listener.ini"
    ini.write_text(
        "\ufeff[listener]\n"
        "url = https://ntfy.example\n"
        "topic = from_ini   ; inline comment\n"
        "token = tk_from_ini\n"
        "sounds_dir = snd\n"
        "ring_max_age_minutes = 5\n"
        "startup_toast = no\n"
        "log_file = -\n",
        encoding="utf-8",
    )
    cfg = L.load_config(_args(["--config", str(ini)]), env={})
    assert cfg.url == "https://ntfy.example"
    assert cfg.topic == "from_ini" and cfg.token == "tk_from_ini"
    assert cfg.sounds_dir == (tmp_path / "snd").resolve()
    assert cfg.ring_sound == cfg.sounds_dir / "ring.wav" and cfg.chime_sound == cfg.sounds_dir / "chime.wav"
    assert cfg.ring_max_age_seconds == 300 and cfg.startup_toast is False and cfg.log_file is None

    cfg = L.load_config(_args(["--config", str(ini)]), env={"NTFY_TOPIC": "from_env", "NTFY_TOKEN": ""})
    assert cfg.topic == "from_env" and cfg.token == "tk_from_ini"   # empty env doesn't override

    cfg = L.load_config(_args(["--config", str(ini), "--topic", "from_cli", "--ring-sound", "/x/r.wav"]),
                        env={"NTFY_TOPIC": "from_env"})
    assert cfg.topic == "from_cli" and cfg.ring_sound == Path("/x/r.wav")


def test_config_ini_without_section_and_defaults(tmp_path):
    ini = tmp_path / "listener.ini"
    ini.write_text("topic = bare_topic\n", encoding="utf-8")
    cfg = L.load_config(_args(["--config", str(ini)]), env={})
    assert cfg.topic == "bare_topic" and cfg.url == L.DEFAULT_URL and cfg.token == ""
    assert cfg.ring_timeout_seconds == 0 and cfg.ring_max_age_seconds == 900
    cfg = L.load_config(_args(["--config", str(tmp_path / "missing.ini")]), env={})
    assert cfg.topic == ""


def test_main_without_topic_fails_cleanly(tmp_path):
    rc = L.main(["--config", str(tmp_path / "none.ini"), "--log-file", "-"], handler=lambda m, lvl: None)
    assert rc == 2


# --------------------------------------------------------------------------- fake ntfy server


class FakeNtfy:
    """Streams scripted JSON lines, one script per connection, then closes the connection."""

    def __init__(self, connections):
        self.connections = connections      # list of (status, [line dicts])
        self.requests: list[tuple[str, dict]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                outer.requests.append((self.path, dict(self.headers)))
                idx = len(outer.requests) - 1
                if idx < len(outer.connections):
                    status, lines = outer.connections[idx]
                else:   # unscripted reconnect: idle stream for a moment
                    status, lines = 200, [{"id": "o", "time": int(time.time()), "event": "open"}]
                if status != 200:
                    body = json.dumps({"code": status * 100 + 1, "http": status, "error": "unauthorized"}).encode()
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.end_headers()
                try:
                    for line in lines:
                        data = line if isinstance(line, bytes) else (json.dumps(line) + "\n").encode()
                        self.wfile.write(data)
                        self.wfile.flush()
                        time.sleep(0.01)
                    if idx >= len(outer.connections):
                        time.sleep(0.5)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def query(self, i) -> dict:
        return urllib.parse.parse_qs(urllib.parse.urlsplit(self.requests[i][0]).query)


def _open(t=1_700_000_000):
    return {"id": "op1", "time": t, "event": "open", "topic": "news_topic"}


def _keepalive():
    return {"id": "ka1", "time": int(time.time()), "event": "keepalive", "topic": "news_topic"}


def _message(mid, priority=5, **kw):
    return {"id": mid, "time": int(time.time()), "event": "message", "topic": "news_topic",
            "title": f"title {mid}", "message": "body", "priority": priority, **kw}


def test_main_once_with_stub_handler(tmp_path):
    got = []
    conns = [(200, [_open(), _keepalive(), b"\n", b"garbage\n", _keepalive(),
                    _message("m1", 5, tags=["rotating_light", "na-ring"], click="https://example.com/a"),
                    _message("m2", 4)])]
    with FakeNtfy(conns) as srv:
        rc = L.main(["--config", str(tmp_path / "none.ini"), "--url", srv.url, "--topic", "news_topic",
                     "--token", "tk_secret_123", "--once", "--log-file", str(tmp_path / "l.log")],
                    handler=lambda m, level: got.append((m["id"], level)))
    assert rc == 0
    assert got == [("m1", "urgent")]
    path, headers = srv.requests[0]
    assert path == "/news_topic/json"                  # first start: no since
    assert headers.get("Authorization") == "Bearer tk_secret_123"
    assert "tk_secret_123" not in (tmp_path / "l.log").read_text()


def test_no_auth_header_without_token(tmp_path):
    got = []
    with FakeNtfy([(200, [_open(), _message("m1", 2)])]) as srv:
        L.main(["--config", str(tmp_path / "none.ini"), "--url", srv.url, "--topic", "news_topic", "--once",
                "--log-file", "-"], handler=lambda m, level: got.append(level))
    assert got == ["quiet"]
    assert "Authorization" not in srv.requests[0][1]


def _subscriber(srv, handler, stop_after):
    return L.Subscriber(srv.url, "news_topic", "", handler, stop_after=stop_after,
                        backoff_initial=0.01, backoff_max=0.05, read_timeout=5)


def test_reconnect_resumes_with_since_last_message_id():
    got = []
    conns = [
        (200, [_open(), _message("m1", 5), _keepalive()]),          # then the link drops
        (200, [_open(), _message("m1", 5), _message("m2", 4)]),      # server replays m1: must be ignored
    ]
    with FakeNtfy(conns) as srv:
        sub = _subscriber(srv, lambda m, level: got.append((m["id"], level)), stop_after=2)
        t = threading.Thread(target=sub.run, daemon=True)
        t.start()
        t.join(10)
        assert not t.is_alive()
    assert got == [("m1", "urgent"), ("m2", "normal")]
    assert "since" not in srv.query(0)
    assert srv.query(1)["since"] == ["m1"]


def test_reconnect_before_any_message_uses_open_time():
    got = []
    conns = [(200, [_open(1_700_000_123), _keepalive()]), (200, [_open(), _message("m1", 4)])]
    with FakeNtfy(conns) as srv:
        sub = _subscriber(srv, lambda m, level: got.append(m["id"]), stop_after=1)
        t = threading.Thread(target=sub.run, daemon=True)
        t.start()
        t.join(10)
    assert got == ["m1"]
    assert "since" not in srv.query(0)
    assert srv.query(1)["since"] == ["1700000123"]


def test_http_error_is_retried(caplog):
    got = []
    with FakeNtfy([(401, []), (200, [_open(), _message("m1", 5)])]) as srv:
        with caplog.at_level("ERROR", logger="newsalert_listener"):
            sub = _subscriber(srv, lambda m, level: got.append(m["id"]), stop_after=1)
            t = threading.Thread(target=sub.run, daemon=True)
            t.start()
            t.join(10)
    assert got == ["m1"]
    assert len(srv.requests) == 2
    assert any("401" in r.getMessage() and "token" in r.getMessage() for r in caplog.records)


def test_stale_message_is_delivered_quietly_and_marked():
    got = []
    old = dict(_message("m1", 5), time=int(time.time()) - 7200)
    with FakeNtfy([(200, [_open(), old])]) as srv:
        sub = _subscriber(srv, lambda m, level: got.append((level, m.get("_stale"))), stop_after=1)
        sub.run()
    assert got == [("quiet", True)]
    assert "offline" in L.display_body(dict(old, _stale=True))


def test_handler_exception_does_not_stop_subscription():
    got = []

    def handler(m, level):
        got.append(m["id"])
        if m["id"] == "m1":
            raise RuntimeError("boom")

    with FakeNtfy([(200, [_open(), _message("m1"), _message("m2")])]) as srv:
        _subscriber(srv, handler, stop_after=2).run()
    assert got == ["m1", "m2"]


def test_status_callbacks_report_connect():
    events = []
    with FakeNtfy([(200, [_open(), _message("m1")])]) as srv:
        sub = _subscriber(srv, lambda m, level: None, stop_after=1)
        sub.on_status = lambda status, detail: events.append(status)
        sub.run()
    assert events == ["connected"]


# --------------------------------------------------------------------------- stdin mode (used by alert/local.py)


def test_stdin_mode_accepts_local_notifier_arguments(tmp_path, monkeypatch):
    lines = [json.dumps(_message("local-1", 5)), json.dumps(_keepalive()), "", json.dumps(_message("local-2", 2))]
    fake_stdin = types.SimpleNamespace(buffer=io.BytesIO(("\n".join(lines) + "\n").encode()))
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    got = []
    rc = L.main(["--stdin", "--ring-sound", str(tmp_path / "r.wav"), "--chime-sound", str(tmp_path / "c.wav"),
                 "--log-file", "-", "--config", str(tmp_path / "none.ini")],
                handler=lambda m, level: got.append((m["id"], level)))
    assert rc == 0
    assert got == [("local-1", "urgent"), ("local-2", "quiet")]


def test_test_ring_and_chime_flags_use_handler(tmp_path):
    got = []
    base = ["--config", str(tmp_path / "none.ini"), "--log-file", "-"]
    assert L.main([*base, "--test-ring"], handler=lambda m, level: got.append((level, L.kind_of(m)))) == 0
    assert L.main([*base, "--test-chime"], handler=lambda m, level: got.append((level, L.kind_of(m)))) == 0
    assert got == [("urgent", "test"), ("normal", "test")]


# --------------------------------------------------------------------------- alert handling


class FakePlayer:
    def __init__(self):
        self.ringing = False
        self.chiming = False
        self.rings = 0
        self.chimes = 0

    def start_ring(self, timeout_seconds=0.0):
        self.rings += 1
        self.ringing = True

    def stop_ring(self):
        self.ringing = False

    def play_chime(self):
        self.chimes += 1


class FakeToaster:
    pending = False

    def __init__(self):
        self.shown = []

    def show(self, title, body, url=None, level="quiet"):
        self.shown.append((title, level, url))


def test_desktop_alerter_headless_levels():
    player, toaster = FakePlayer(), FakeToaster()
    alerter = L.DesktopAlerter(L.Config(), None, player, toaster)
    alerter.handle(msg(5, title="U", click="https://example.com/u"), "urgent")
    alerter.handle(msg(4, title="N"), "normal")
    alerter.handle(msg(2, title="Q"), "quiet")
    assert player.rings == 1 and player.chimes == 1
    assert toaster.shown == [("U", "urgent", "https://example.com/u"), ("N", "normal", None), ("Q", "quiet", None)]
    assert alerter.busy   # still ringing


def test_toast_command_passes_text_only_through_environment():
    cmd, env = L.toast_command('Title "<&>" \'x\'', "Body; $(rm -rf) `whoami`", "file:///etc/passwd", long=True)
    script = base64.b64decode(cmd[-1]).decode("utf-16-le")
    assert script == L.TOAST_PS
    assert "Title" not in " ".join(cmd) and "whoami" not in script
    assert env["NA_TOAST_TITLE"].startswith("Title") and env["NA_TOAST_BODY"].startswith("Body")
    assert env["NA_TOAST_URL"] == ""          # only http(s) links can be launched from a toast
    assert env["NA_TOAST_LONG"] == "1"
    assert "-NoProfile" in cmd and "-EncodedCommand" in cmd


def test_toaster_falls_back_when_toast_fails():
    failed = []
    done = threading.Event()

    def on_failure(title, body, url):
        failed.append(title)
        done.set()

    toaster = L.Toaster(on_failure=on_failure, show=lambda *a: False)
    toaster.show("T", "B", None, "quiet")
    assert done.wait(5)
    assert failed == ["T"]


def test_single_instance_lock():
    key = f"test-{time.time()}"
    first = L.acquire_single_instance_lock(key)
    assert first is not None
    try:
        assert L.acquire_single_instance_lock(key) is None
    finally:
        first.close()
    again = L.acquire_single_instance_lock(key)
    assert again is not None
    again.close()


# --------------------------------------------------------------------------- ring window (with a fake tkinter)


class FakeWidget:
    instances: list["FakeWidget"] = []

    def __init__(self, *args, **kw):
        self.kw = dict(kw)
        self.calls: list[tuple] = []
        self.destroyed = False
        self.inserted: list[str] = []
        FakeWidget.instances.append(self)

    def configure(self, **kw):
        self.kw.update(kw)

    config = configure

    def insert(self, index, text, *tags):
        self.inserted.append(text)

    def destroy(self):
        self.destroyed = True

    def after(self, ms, fn=None, *args):
        self.calls.append(("after", ms, fn))

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def noop(*a, **kw):
            self.calls.append((name, a, kw))
            return 0
        return noop


def fake_tk_module():
    FakeWidget.instances = []
    return types.SimpleNamespace(Tk=FakeWidget, Toplevel=FakeWidget, Frame=FakeWidget, Label=FakeWidget,
                                 Button=FakeWidget, Text=FakeWidget, Scrollbar=FakeWidget)


def _buttons(text):
    return [w for w in FakeWidget.instances if w.kw.get("text") == text and "command" in w.kw]


def test_ring_window_stacks_alerts_and_buttons_stop_ring(monkeypatch):
    opened = []
    monkeypatch.setattr(L.webbrowser, "open", lambda url, new=0: opened.append(url))
    player = FakePlayer()
    ui = L.TkUI(fake_tk_module(), player)

    ui.show_urgent(msg(5, id="a", title="First", click="https://example.com/1"))
    first_window = ui.ring_window
    ui.show_urgent(msg(5, id="b", title="Second", click="https://example.com/2"))
    assert ui.ring_window is first_window                       # stacked, not a second window
    assert len(first_window.alerts) == 2
    assert first_window.header.kw["text"] == "2 URGENT NEWS ALERTS"
    assert player.ringing and player.rings == 2                 # second call only extends
    assert any("First" in t for t in first_window.text.inserted)
    assert ("attributes", ("-topmost", True), {}) in first_window.win.calls

    # Open with several alerts: opens newest, stops ring, keeps the list (no longer topmost)
    first_window.open_button.kw["command"]()
    assert opened == ["https://example.com/2"]
    assert not player.ringing and ui.ring_window is first_window
    assert ("attributes", ("-topmost", False), {}) in first_window.win.calls

    # A new urgent alert rings again; Dismiss closes everything
    ui.show_urgent(msg(5, id="c", title="Third"))
    assert player.ringing
    dismiss = [b for b in _buttons("Dismiss")][-1]
    dismiss.kw["command"]()
    assert not player.ringing and first_window.win.destroyed and ui.ring_window is None
    assert not ui.busy


def test_ring_window_single_alert_open_closes(monkeypatch):
    opened = []
    monkeypatch.setattr(L.webbrowser, "open", lambda url, new=0: opened.append(url))
    player = FakePlayer()
    ui = L.TkUI(fake_tk_module(), player)
    ui.show_urgent(msg(5, title="Only", actions=[{"action": "view", "label": "ANN", "url": "https://example.com/ann"}]))
    win = ui.ring_window
    win.open_latest()
    assert opened == ["https://example.com/ann"] and not player.ringing
    assert win.win.destroyed and ui.ring_window is None


def test_popup_fallback_is_tracked_and_closes():
    ui = L.TkUI(fake_tk_module(), FakePlayer())
    ui.show_popup("Title", "Body", "https://example.com")
    assert ui.busy and len(ui.popups) == 1
    close = _buttons("Close")[-1]
    close.kw["command"]()
    assert not ui.popups
