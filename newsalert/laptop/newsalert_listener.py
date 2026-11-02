#!/usr/bin/env python3
"""newsalert laptop listener: subscribe to your ntfy topic and RING when urgent news arrives.

Single file, Python 3.10+ standard library only. Copy this file, listener.ini and the
two sounds (ring.wav, chime.wav) to your laptop. See docs/laptop-setup.md.

  priority 5 (urgent)  -> ring.wav loops + a topmost window with Open / Dismiss
                          (keeps ringing until you press a button) + a toast
  priority 4 (normal)  -> chime.wav once + a toast
  priority 1-3 (quiet) -> toast only, no sound

Usage:
  python newsalert_listener.py                 # listen (settings from listener.ini)
  python newsalert_listener.py --test-ring     # try the urgent ring + window, no ntfy needed
  python newsalert_listener.py --test-chime    # try the chime + toast
  pythonw newsalert_listener.py                # same as the first, without a console window

Settings, highest priority first: command line, environment (NTFY_URL, NTFY_TOPIC,
NTFY_TOKEN, NEWSALERT_SOUNDS_DIR), listener.ini next to this file, defaults.
This program only listens: it never posts anything anywhere.
"""

from __future__ import annotations

import argparse
import base64
import collections
import configparser
import dataclasses
import hashlib
import http.client
import json
import logging
import logging.handlers
import os
import queue
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Callable, Optional

__version__ = "0.2.0"

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_URL = "https://ntfy.sh"
USER_AGENT = f"newsalert-listener/{__version__}"
READ_TIMEOUT = 90.0            # ntfy sends a keepalive every ~45 s; silence beyond this = dead link
HEADLESS_RING_SECONDS = 120.0  # without a window nothing can be clicked, so stop ringing eventually
OUTAGE_WARN_SECONDS = 300.0    # tell the owner when ntfy has been unreachable this long
CREATE_NO_WINDOW = 0x08000000  # Windows: run PowerShell without flashing a console

log = logging.getLogger("newsalert_listener")

Handler = Callable[[dict, str], None]   # handler(ntfy_message, level)

# =========================================================================== pure logic
# Everything in this section is side-effect free and unit-tested on any OS.

PRIORITY_NAMES = {"max": 5, "urgent": 5, "high": 4, "default": 3, "low": 2, "min": 1}
KIND_PREFIX = "na-"
KINDS = ("ring", "followup", "retraction", "health", "test", "digest")


def parse_line(line: bytes | str) -> Optional[dict]:
    """One line of ntfy's /json stream -> dict, or None for blank/garbage lines."""
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def priority_of(msg: dict) -> int:
    """ntfy omits `priority` when it is the default (3)."""
    raw = msg.get("priority", 3)
    if isinstance(raw, str):
        name = raw.strip().lower()
        if name in PRIORITY_NAMES:
            return PRIORITY_NAMES[name]
        try:
            raw = int(name)
        except ValueError:
            return 3
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return 3
    return min(5, max(1, int(raw)))


def tags_of(msg: dict) -> list[str]:
    tags = msg.get("tags") or []
    if isinstance(tags, str):
        tags = tags.split(",")
    return [str(t).strip() for t in tags if str(t).strip()]


def classify(msg: Any) -> Optional[str]:
    """'urgent' | 'normal' | 'quiet' for a message event, None for anything else.

    Priority decides (so curl / the phone app / other tools behave predictably);
    the na-* kind tag is only used for labels.
    """
    if not isinstance(msg, dict) or msg.get("event") != "message":
        return None   # open, keepalive, poll_request, message_delete, ...
    p = priority_of(msg)
    if p >= 5:
        return "urgent"
    if p == 4:
        return "normal"
    return "quiet"


def kind_of(msg: dict) -> Optional[str]:
    """newsalert alert kind from its na-<kind> tag ('ring', 'test', ...), None for foreign messages."""
    for t in tags_of(msg):
        if t.startswith(KIND_PREFIX) and t[len(KIND_PREFIX):] in KINDS:
            return t[len(KIND_PREFIX):]
    return None


def is_stale(msg: dict, now: float, max_age_seconds: float) -> bool:
    """True when a message is older than max_age (e.g. delivered after the laptop woke up)."""
    if max_age_seconds <= 0:
        return False
    try:
        sent = float(msg.get("time") or 0)
    except (TypeError, ValueError):
        return False
    return sent > 0 and now - sent > max_age_seconds


def effective_level(msg: Any, now: Optional[float] = None, max_age_seconds: float = 900) -> Optional[str]:
    """classify(), but old urgent/normal messages are shown quietly instead of ringing."""
    level = classify(msg)
    if level in ("urgent", "normal") and is_stale(msg, time.time() if now is None else now, max_age_seconds):
        return "quiet"
    return level


def web_url(url: Any) -> Optional[str]:
    """Only http(s) links are ever opened: a message must not be able to launch file:// or apps."""
    if isinstance(url, str) and url.strip().lower().startswith(("http://", "https://")):
        return url.strip()
    return None


def view_links(msg: dict) -> list[tuple[str, str]]:
    out = []
    for a in msg.get("actions") or []:
        if isinstance(a, dict) and a.get("action") == "view":
            url = web_url(a.get("url"))
            if url:
                out.append((str(a.get("label") or "Open"), url))
    return out[:3]


def click_url(msg: dict) -> Optional[str]:
    url = web_url(msg.get("click"))
    if url:
        return url
    links = view_links(msg)
    return links[0][1] if links else None


def display_title(msg: dict) -> str:
    title = str(msg.get("title") or "").strip()
    return title or "newsalert"


def display_body(msg: dict) -> str:
    body = str(msg.get("message") or "").strip()
    if msg.get("_stale"):
        body = "(arrived while this laptop was offline)\n" + body
    return body


def subscribe_url(base: str, topic: str, since: Optional[str] = None) -> str:
    url = f"{base.rstrip('/')}/{urllib.parse.quote(topic, safe='')}/json"
    if since:
        url += "?" + urllib.parse.urlencode({"since": since})
    return url


def normalize_topic(url: str, topic: str) -> tuple[str, str]:
    """Accept 'mytopic' or a pasted 'https://ntfy.sh/mytopic'."""
    topic = (topic or "").strip().strip("/")
    if topic.lower().startswith(("http://", "https://")):
        base, _, topic = topic.rpartition("/")
        return base, topic
    return url, topic


def valid_topic(topic: str) -> bool:
    return 1 <= len(topic) <= 64 and all(c.isascii() and (c.isalnum() or c in "-_") for c in topic)


# =========================================================================== settings


@dataclasses.dataclass
class Config:
    url: str = DEFAULT_URL
    topic: str = ""
    token: str = ""
    sounds_dir: Path = SCRIPT_DIR / "sounds"
    ring_sound: Path = SCRIPT_DIR / "sounds" / "ring.wav"
    chime_sound: Path = SCRIPT_DIR / "sounds" / "chime.wav"
    ring_max_age_minutes: float = 15.0
    ring_timeout_minutes: float = 0.0     # 0 = ring until a button is pressed
    startup_toast: bool = True
    log_file: Optional[Path] = SCRIPT_DIR / "newsalert_listener.log"

    @property
    def ring_timeout_seconds(self) -> float:
        return max(0.0, self.ring_timeout_minutes * 60)

    @property
    def ring_max_age_seconds(self) -> float:
        return max(0.0, self.ring_max_age_minutes * 60)


INI_KEYS = (
    "url", "topic", "token", "sounds_dir", "ring_sound", "chime_sound",
    "ring_max_age_minutes", "ring_timeout_minutes", "startup_toast", "log_file",
)
ENV_KEYS = {"url": "NTFY_URL", "topic": "NTFY_TOPIC", "token": "NTFY_TOKEN", "sounds_dir": "NEWSALERT_SOUNDS_DIR"}


def default_sounds_dir() -> Path:
    for cand in (SCRIPT_DIR / "sounds", SCRIPT_DIR, SCRIPT_DIR.parent / "config" / "sounds"):
        if (cand / "ring.wav").exists():
            return cand
    return SCRIPT_DIR / "sounds"


def read_ini(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")     # Notepad may add a BOM
    parser = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";", "#"))
    try:
        parser.read_string(text)
    except configparser.MissingSectionHeaderError:
        parser.read_string("[listener]\n" + text)
    section = parser["listener"] if parser.has_section("listener") else parser.defaults()
    out = {}
    for key in INI_KEYS:
        value = section.get(key)
        if value is not None and value.strip() != "":
            value = value.strip()
            if (key in ("sounds_dir", "ring_sound", "chime_sound", "log_file") and value.lower() not in ("-", "none")
                    and not Path(value).is_absolute()):
                value = str((path.parent / value).resolve())
            out[key] = value
    return out


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "yes", "true", "on")


def load_config(args: argparse.Namespace, env: Optional[dict] = None) -> Config:
    env = os.environ if env is None else env
    ini_path = Path(args.config) if getattr(args, "config", None) else SCRIPT_DIR / "listener.ini"
    values: dict[str, Any] = read_ini(ini_path)
    for key, var in ENV_KEYS.items():
        if env.get(var, "").strip():
            values[key] = env[var].strip()
    for key in INI_KEYS:
        cli = getattr(args, key, None)
        if cli is not None:
            values[key] = cli

    cfg = Config()
    cfg.url = str(values.get("url") or DEFAULT_URL).strip()
    cfg.url, cfg.topic = normalize_topic(cfg.url, str(values.get("topic") or ""))
    cfg.token = str(values.get("token") or "").strip()
    cfg.sounds_dir = Path(values["sounds_dir"]) if values.get("sounds_dir") else default_sounds_dir()
    cfg.ring_sound = Path(values["ring_sound"]) if values.get("ring_sound") else cfg.sounds_dir / "ring.wav"
    cfg.chime_sound = Path(values["chime_sound"]) if values.get("chime_sound") else cfg.sounds_dir / "chime.wav"
    for key in ("ring_max_age_minutes", "ring_timeout_minutes"):
        if key in values:
            try:
                setattr(cfg, key, float(values[key]))
            except ValueError:
                log.warning("setting %s=%r is not a number; using %s", key, values[key], getattr(cfg, key))
    if "startup_toast" in values:
        cfg.startup_toast = _as_bool(values["startup_toast"])
    if "log_file" in values:
        cfg.log_file = Path(values["log_file"]) if str(values["log_file"]).strip() not in ("", "-", "none") else None
    return cfg


# =========================================================================== logging


class _Redact(logging.Filter):
    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s and len(s) >= 4]

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secrets:
            text = record.getMessage()
            for s in self._secrets:
                text = text.replace(s, "***")
            record.msg, record.args = text, ()
        return True


def setup_logging(log_file: Optional[Path], verbose: bool = False, secrets: tuple[str, ...] = ()) -> None:
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    redact = _Redact(list(secrets))
    handlers: list[logging.Handler] = []
    if sys.stderr is not None:          # pythonw has no console
        handlers.append(logging.StreamHandler(sys.stderr))
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.handlers.RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"))
        except OSError:
            pass
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(redact)
        log.addHandler(h)


# =========================================================================== sound


def posix_player(path: Path) -> Optional[list[str]]:
    if IS_MAC:
        return ["afplay", str(path)] if shutil.which("afplay") else None
    for cmd in (["paplay"], ["pw-play"], ["aplay", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
        if shutil.which(cmd[0]):
            return [*cmd, str(path)]
    return None


class SoundPlayer:
    """Loops ring.wav until stop_ring(); plays chime.wav once. Never blocks the caller."""

    def __init__(self, ring: Path, chime: Path) -> None:
        self.ring_path = ring
        self.chime_path = chime
        self._lock = threading.Lock()
        self._ringing = False
        self._stop = threading.Event()
        self._timer: Optional[threading.Timer] = None
        self._chime_until = 0.0
        self._warned: set[str] = set()

    def _warn_once(self, key: str, text: str, *args: Any) -> None:
        if key not in self._warned:
            self._warned.add(key)
            log.warning(text, *args)

    def check_files(self) -> None:
        for p in (self.ring_path, self.chime_path):
            if not p.exists():
                self._warn_once(str(p), "sound file missing: %s (copy ring.wav/chime.wav there, or set sounds_dir)", p)

    @property
    def ringing(self) -> bool:
        return self._ringing

    @property
    def chiming(self) -> bool:
        return time.monotonic() < self._chime_until

    def start_ring(self, timeout_seconds: float = 0.0) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if timeout_seconds > 0:
                self._timer = threading.Timer(timeout_seconds, self.stop_ring)
                self._timer.daemon = True
                self._timer.start()
            if self._ringing:
                return
            self._ringing = True
            self._stop.clear()
            if not self.ring_path.exists():
                self.check_files()
            if IS_WINDOWS:
                try:
                    import winsound
                    winsound.PlaySound(str(self.ring_path), winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC)
                except Exception as exc:  # noqa: BLE001 - never crash on audio
                    self._warn_once("winsound", "could not play ring: %s", exc)
            else:
                threading.Thread(target=self._posix_ring_loop, name="ring", daemon=True).start()
        log.info("ringing")

    def stop_ring(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if not self._ringing:
                return
            self._ringing = False
            self._stop.set()
            if IS_WINDOWS:
                try:
                    import winsound
                    winsound.PlaySound(None, 0)
                except Exception:  # noqa: BLE001
                    pass
        log.info("ring stopped")

    def _posix_ring_loop(self) -> None:
        cmd = posix_player(self.ring_path)
        if cmd is None:
            self._warn_once("player", "no sound player found (install pulseaudio-utils/alsa-utils, or afplay on macOS)")
            self._ringing = False
            return
        failures = 0
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError as exc:
                self._warn_once("player-run", "sound player failed: %s", exc)
                break
            while proc.poll() is None:
                if self._stop.wait(0.1):
                    proc.terminate()
                    break
            if proc.returncode not in (0, None, -15) and time.monotonic() - t0 < 0.3:
                failures += 1
                if failures >= 3:
                    self._warn_once("player-fail", "sound player keeps failing (%s); giving up on sound", cmd[0])
                    break
                self._stop.wait(1.0)
            else:
                failures = 0
        self._ringing = False

    def play_chime(self) -> None:
        if self._ringing:
            return     # winsound plays one sound at a time; don't cut the ring
        if not self.chime_path.exists():
            self.check_files()
        self._chime_until = time.monotonic() + 1.2
        if IS_WINDOWS:
            try:
                import winsound
                winsound.PlaySound(str(self.chime_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as exc:  # noqa: BLE001
                self._warn_once("winsound-chime", "could not play chime: %s", exc)
            return
        cmd = posix_player(self.chime_path)
        if cmd is None:
            self._warn_once("player", "no sound player found (install pulseaudio-utils/alsa-utils, or afplay on macOS)")
            return
        try:
            subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self._warn_once("player-run", "sound player failed: %s", exc)


# =========================================================================== toasts

# Windows PowerShell 5.1 can show native toasts through WinRT with no extra modules.
# Text arrives via environment variables, so nothing in a message is ever parsed as code.
TOAST_PS = r"""
$ErrorActionPreference = 'Stop'
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
function Esc([string]$s) { if ($s) { return [System.Security.SecurityElement]::Escape($s) } else { return '' } }
$title = Esc $env:NA_TOAST_TITLE
$body = Esc $env:NA_TOAST_BODY
$url = Esc $env:NA_TOAST_URL
$attrs = ''
if ($url) { $attrs += ' activationType="protocol" launch="' + $url + '"' }
if ($env:NA_TOAST_LONG -eq '1') { $attrs += ' duration="long"' }
$xml = '<toast' + $attrs + '><visual><binding template="ToastGeneric"><text>' + $title + '</text><text>' + $body + '</text></binding></visual><audio silent="true"/></toast>'
$doc = [Windows.Data.Xml.Dom.XmlDocument]::new()
$doc.LoadXml($xml)
$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show($toast)
"""


def _short(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def powershell_exe() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    exe = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(exe) if exe.exists() else (shutil.which("powershell") or "powershell.exe")


def toast_command(title: str, body: str, url: Optional[str], long: bool = False) -> tuple[list[str], dict[str, str]]:
    encoded = base64.b64encode(TOAST_PS.encode("utf-16-le")).decode("ascii")
    cmd = [powershell_exe(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]
    env = dict(os.environ)
    env.update({
        "NA_TOAST_TITLE": _short(title, 200),
        "NA_TOAST_BODY": _short(body, 400),
        "NA_TOAST_URL": web_url(url) or "",
        "NA_TOAST_LONG": "1" if long else "0",
    })
    return cmd, env


def show_toast(title: str, body: str, url: Optional[str] = None, level: str = "quiet") -> bool:
    """Native notification. Returns False if it could not be shown."""
    try:
        if IS_WINDOWS:
            cmd, env = toast_command(title, body, url, long=level == "urgent")
            r = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=20, creationflags=CREATE_NO_WINDOW)
            if r.returncode != 0:
                log.warning("toast failed: %s", r.stderr.decode("utf-8", "replace").strip()[-300:])
            return r.returncode == 0
        if IS_MAC:
            if not shutil.which("osascript"):
                return False
            script = ['-e', 'on run argv', '-e', 'display notification (item 2 of argv) with title (item 1 of argv)', '-e', 'end run']
            r = subprocess.run(["osascript", *script, _short(title, 200), _short(body, 400)],
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
            return r.returncode == 0
        if not shutil.which("notify-send"):
            return False
        urgency = {"urgent": "critical", "normal": "normal"}.get(level, "low")
        r = subprocess.run(["notify-send", "-a", "newsalert", "-u", urgency, "--", _short(title, 200), _short(body, 400)],
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("toast failed: %s", exc)
        return False


class Toaster:
    """Shows notifications one at a time on a worker thread; reports failures to a fallback."""

    def __init__(self, on_failure: Optional[Callable[[str, str, Optional[str]], None]] = None,
                 show: Callable[..., bool] = show_toast) -> None:
        self._q: "queue.Queue[tuple[str, str, Optional[str], str]]" = queue.Queue()
        self._on_failure = on_failure
        self._show = show
        self._pending = 0
        self._lock = threading.Lock()
        threading.Thread(target=self._run, name="toaster", daemon=True).start()

    @property
    def pending(self) -> bool:
        return self._pending > 0

    def show(self, title: str, body: str, url: Optional[str] = None, level: str = "quiet") -> None:
        with self._lock:
            self._pending += 1
        self._q.put((title, body, url, level))

    def _run(self) -> None:
        while True:
            title, body, url, level = self._q.get()
            try:
                ok = self._show(title, body, url, level)
                if not ok and self._on_failure is not None:
                    self._on_failure(title, body, url)
            except Exception:  # noqa: BLE001
                log.exception("toast worker error")
            finally:
                with self._lock:
                    self._pending -= 1


# =========================================================================== window (Tkinter)

RED = "#c62828"
FONT = "Segoe UI" if IS_WINDOWS else ("Helvetica" if IS_MAC else "DejaVu Sans")


def open_in_browser(url: Optional[str]) -> None:
    url = web_url(url)
    if not url:
        return
    try:
        webbrowser.open(url, new=2)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not open browser: %s", exc)


class RingWindow:
    """One topmost window for all urgent alerts; new alerts stack at the top of the list."""

    def __init__(self, ui: "TkUI") -> None:
        self.ui = ui
        tk = ui.tk
        self.alerts: list[dict] = []
        self.closed = False
        self._placed = False
        self._keeping_on_top = False
        self.win = tk.Toplevel(ui.root)
        self.win.title("newsalert - URGENT")
        self.win.configure(bg=RED)
        self.win.protocol("WM_DELETE_WINDOW", self.dismiss)
        self.win.bind("<Escape>", lambda _e: self.dismiss())
        self.win.bind("<Return>", lambda _e: self.open_latest())

        self.header = tk.Label(self.win, text="", font=(FONT, 20, "bold"), bg=RED, fg="white",
                               anchor="w", padx=16, pady=10)
        self.header.pack(fill="x")

        body = tk.Frame(self.win, bg="white")
        body.pack(fill="both", expand=True)
        self.text = tk.Text(body, wrap="word", width=74, height=15, bg="white", relief="flat",
                            padx=14, pady=10, font=(FONT, 11), cursor="arrow")
        scroll = tk.Scrollbar(body, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure("title", font=(FONT, 14, "bold"), spacing1=4, spacing3=6)
        self.text.tag_configure("meta", foreground="#757575", font=(FONT, 9))
        self.text.tag_configure("sep", foreground="#bdbdbd")
        self.text.configure(state="disabled")

        bar = tk.Frame(self.win, bg=RED, padx=12, pady=10)
        bar.pack(fill="x")
        self.open_button = tk.Button(bar, text="Open", width=14, font=(FONT, 13, "bold"), command=self.open_latest)
        self.open_button.pack(side="left")
        tk.Button(bar, text="Dismiss", width=14, font=(FONT, 13, "bold"), command=self.dismiss).pack(side="right")

    # -- content
    def add(self, msg: dict) -> None:
        tk = self.ui.tk
        self.alerts.append(msg)
        t = self.text
        t.configure(state="normal")
        t.mark_set("na_insert", "1.0")
        t.mark_gravity("na_insert", "right")
        t.insert("na_insert", display_title(msg) + "\n", ("title",))
        received = time.strftime("%H:%M:%S")
        kind = kind_of(msg)
        meta = f"received {received}" + (" · TEST" if kind == "test" else "")
        t.insert("na_insert", meta + "\n", ("meta",))
        t.insert("na_insert", display_body(msg) + "\n")
        url = click_url(msg)
        if url:
            t.window_create("na_insert", window=tk.Button(t, text="Open", command=lambda u=url: self.open(u)), padx=2, pady=4)
        for label, link in view_links(msg):
            if link != url:
                t.window_create("na_insert", window=tk.Button(t, text=_short(label, 30), command=lambda u=link: self.open(u)),
                                padx=2, pady=4)
        t.insert("na_insert", "\n" + "─" * 60 + "\n", ("sep",))
        t.configure(state="disabled")
        t.yview_moveto(0)
        n = len(self.alerts)
        self.header.configure(text="URGENT NEWS ALERT" if n == 1 else f"{n} URGENT NEWS ALERTS")
        self.open_button.configure(state="normal" if self._latest_url() else "disabled")

    def _latest_url(self) -> Optional[str]:
        for msg in reversed(self.alerts):
            url = click_url(msg)
            if url:
                return url
        return None

    # -- presentation
    def present(self) -> None:
        w = self.win
        w.deiconify()
        if not self._placed:    # centre once; don't jump if the owner moved it
            self._placed = True
            w.update_idletasks()
            x = max(0, (w.winfo_screenwidth() - w.winfo_reqwidth()) // 2)
            y = max(0, (w.winfo_screenheight() - w.winfo_reqheight()) // 3)
            w.geometry(f"+{x}+{y}")
        w.attributes("-topmost", True)
        w.lift()
        try:
            w.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def start_keep_on_top(self) -> None:
        """While ringing, re-assert topmost every few seconds (other apps can steal it)."""
        if not self._keeping_on_top:
            self._keeping_on_top = True
            self.ui.root.after(2500, self._keep_on_top)

    def _keep_on_top(self) -> None:
        if self.closed or not self.ui.player.ringing:
            self._keeping_on_top = False
            return
        try:
            self.win.attributes("-topmost", True)
            self.win.lift()
        except Exception:  # noqa: BLE001
            self._keeping_on_top = False
            return
        self.ui.root.after(2500, self._keep_on_top)

    # -- buttons
    def open(self, url: Optional[str]) -> None:
        self.ui.player.stop_ring()
        open_in_browser(url)
        if len(self.alerts) <= 1:
            self.close()
        else:   # let the browser come to the front; the list stays until Dismiss
            self.win.attributes("-topmost", False)
            self.win.lower()

    def open_latest(self) -> None:
        self.open(self._latest_url())

    def dismiss(self) -> None:
        self.ui.player.stop_ring()
        self.close()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.win.destroy()
        finally:
            self.ui.on_ring_window_closed(self)


class TkUI:
    """Owns the Tk root (main thread only). Other threads use call() to run code here."""

    def __init__(self, tk_module: Any, player: SoundPlayer, ring_timeout_seconds: float = 0.0) -> None:
        self.tk = tk_module
        self.player = player
        self.ring_timeout_seconds = ring_timeout_seconds
        self.root = tk_module.Tk()
        self.root.withdraw()
        self.root.title("newsalert listener")
        self.ring_window: Optional[RingWindow] = None
        self.popups: list[Any] = []
        self._calls: "queue.Queue[tuple[Callable[..., Any], tuple]]" = queue.Queue()
        self.root.after(100, self._pump)

    def call(self, fn: Callable[..., Any], *args: Any) -> None:
        self._calls.put((fn, args))

    def _pump(self) -> None:
        while True:
            try:
                fn, args = self._calls.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception:  # noqa: BLE001 - keep the UI alive
                log.exception("ui callback failed")
        self.root.after(100, self._pump)

    @property
    def busy(self) -> bool:
        return self.ring_window is not None or bool(self.popups) or not self._calls.empty()

    def show_urgent(self, msg: dict) -> None:
        if self.ring_window is None or self.ring_window.closed:
            self.ring_window = RingWindow(self)
        self.ring_window.add(msg)
        self.ring_window.present()
        self.player.start_ring(self.ring_timeout_seconds)
        self.ring_window.start_keep_on_top()

    def on_ring_window_closed(self, window: RingWindow) -> None:
        if self.ring_window is window:
            self.ring_window = None

    def show_popup(self, title: str, body: str, url: Optional[str]) -> None:
        """Small non-modal fallback when the OS toast could not be shown."""
        tk = self.tk
        win = tk.Toplevel(self.root)
        win.title("newsalert")
        win.configure(bg="white", padx=12, pady=10)
        tk.Label(win, text=_short(title, 160), font=(FONT, 11, "bold"), bg="white", wraplength=380,
                 justify="left", anchor="w").pack(fill="x")
        tk.Label(win, text=_short(body, 400), font=(FONT, 10), bg="white", wraplength=380,
                 justify="left", anchor="w").pack(fill="x", pady=(4, 8))
        bar = tk.Frame(win, bg="white")
        bar.pack(fill="x")

        def close() -> None:
            if win in self.popups:
                self.popups.remove(win)
            try:
                win.destroy()
            except Exception:  # noqa: BLE001
                pass

        if web_url(url):
            tk.Button(bar, text="Open", command=lambda: (open_in_browser(url), close())).pack(side="left")
        tk.Button(bar, text="Close", command=close).pack(side="right")
        win.protocol("WM_DELETE_WINDOW", close)
        win.update_idletasks()
        index = len(self.popups)
        self.popups.append(win)
        w, h = max(win.winfo_reqwidth(), 300), win.winfo_reqheight()
        x = win.winfo_screenwidth() - w - 24
        y = max(0, win.winfo_screenheight() - (h + 70) * (index + 1))
        win.geometry(f"+{x}+{y}")
        win.attributes("-topmost", True)
        self.root.after(20000, close)

    def run(self) -> None:
        self.root.mainloop()

    def quit(self) -> None:
        self.root.quit()

    def destroy(self) -> None:
        try:
            self.root.destroy()
        except Exception:  # noqa: BLE001
            pass


def make_ui(player: SoundPlayer, ring_timeout_seconds: float) -> Optional[TkUI]:
    try:
        import tkinter
    except ImportError:
        log.warning("tkinter not available: urgent alerts ring for %ds with a toast, no window", HEADLESS_RING_SECONDS)
        return None
    if IS_WINDOWS:
        try:   # crisp text on high-DPI screens
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    try:
        return TkUI(tkinter, player, ring_timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - e.g. no display on a Linux server
        log.warning("no window possible (%s): urgent alerts ring for %ds with a toast", exc, HEADLESS_RING_SECONDS)
        return None


# =========================================================================== alert handling


class DesktopAlerter:
    """The real handler: sound + window + toast for each message."""

    def __init__(self, cfg: Config, ui: Optional[TkUI], player: SoundPlayer, toaster: Toaster) -> None:
        self.cfg = cfg
        self.ui = ui
        self.player = player
        self.toaster = toaster
        self.headless_ring_seconds = cfg.ring_timeout_seconds or HEADLESS_RING_SECONDS

    def handle(self, msg: dict, level: str) -> None:
        title, body, url = display_title(msg), display_body(msg), click_url(msg)
        if level == "urgent":
            if self.ui is not None:
                self.ui.call(self.ui.show_urgent, msg)
            else:
                self.player.start_ring(self.headless_ring_seconds)
            self.toaster.show(title, body, url, "urgent")
        elif level == "normal":
            self.player.play_chime()
            self.toaster.show(title, body, url, "normal")
        else:
            self.toaster.show(title, body, url, "quiet")

    def on_status(self, status: str, detail: str) -> None:
        if status == "connected" and not self.cfg.startup_toast:
            return
        title = {"connected": "newsalert listener connected", "outage": "newsalert listener: no connection",
                 "restored": "newsalert listener reconnected"}.get(status, "newsalert listener")
        self.toaster.show(title, detail, None, "quiet")

    @property
    def busy(self) -> bool:
        return bool((self.ui and self.ui.busy) or self.player.ringing or self.player.chiming or self.toaster.pending)


# =========================================================================== ntfy subscription


class Subscriber:
    """Streams GET {url}/{topic}/json forever; reconnects with backoff and resumes with since=."""

    def __init__(
        self,
        url: str,
        topic: str,
        token: str,
        handler: Handler,
        *,
        stop_after: Optional[int] = None,
        stop_event: Optional[threading.Event] = None,
        read_timeout: float = READ_TIMEOUT,
        backoff_initial: float = 1.0,
        backoff_max: float = 60.0,
        ring_max_age_seconds: float = 900.0,
        on_status: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.url = url
        self.topic = topic
        self.token = token
        self.handler = handler
        self.stop_after = stop_after
        self.stop_event = stop_event or threading.Event()
        self.read_timeout = read_timeout
        self.backoff_initial = backoff_initial
        self.backoff_max = backoff_max
        self.ring_max_age_seconds = ring_max_age_seconds
        self.on_status = on_status
        self.since: Optional[str] = None      # last message id, or the first stream's open time
        self.handled = 0
        self.connections = 0
        self._seen: "collections.OrderedDict[str, None]" = collections.OrderedDict()
        self._fail_since: Optional[float] = None
        self._failures = 0
        self._outage_reported = False
        self._opener = urllib.request.build_opener()   # honours HTTPS_PROXY / system proxy

    @property
    def done(self) -> bool:
        return self.stop_event.is_set() or (self.stop_after is not None and self.handled >= self.stop_after)

    def _status(self, status: str, detail: str) -> None:
        if self.on_status is not None:
            try:
                self.on_status(status, detail)
            except Exception:  # noqa: BLE001
                log.exception("status callback failed")

    def run(self) -> int:
        delay = self.backoff_initial
        while not self.done:
            got_data = False
            try:
                got_data = self._stream_once()
                if not self.done:
                    log.info("stream closed by server; reconnecting")
            except urllib.error.HTTPError as exc:
                self._log_http_error(exc)
            except (OSError, http.client.HTTPException, ValueError) as exc:   # URLError, timeouts, resets
                log.warning("connection problem: %s", exc)
            if self.done:
                break
            if got_data:
                delay = self.backoff_initial
            self._note_failure()
            wait = delay * (0.8 + 0.4 * random.random())
            log.info("reconnecting in %.1fs", wait)
            if self.stop_event.wait(wait):
                break
            delay = min(self.backoff_max, delay * 2)
        return self.handled

    def _log_http_error(self, exc: urllib.error.HTTPError) -> None:
        try:
            detail = exc.read().decode("utf-8", "replace").strip()[:200]
        except Exception:  # noqa: BLE001
            detail = ""
        hint = ""
        if exc.code in (401, 403):
            hint = " - the topic is protected: set token in listener.ini (an ntfy access token that may read it)"
        elif exc.code == 429:
            hint = " - rate limited by the ntfy server"
        log.error("ntfy refused the subscription: HTTP %s %s%s", exc.code, detail, hint)

    def _note_failure(self) -> None:
        now = time.time()
        self._failures += 1
        if self._fail_since is None:
            self._fail_since = now
        if (not self._outage_reported and self._failures >= 4 and now - self._fail_since >= OUTAGE_WARN_SECONDS):
            self._outage_reported = True
            self._status("outage", f"Can't reach {self.url} for {int((now - self._fail_since) // 60)} min. "
                                   "Alerts are delayed until it reconnects.")

    def _note_connected(self) -> None:
        self.connections += 1
        if self._outage_reported:
            self._status("restored", "Connected again. Missed alerts are being delivered.")
        elif self.connections == 1:
            self._status("connected", f"Listening for alerts from {self.url}.")
        self._fail_since = None
        self._failures = 0
        self._outage_reported = False

    def _remember(self, msg_id: str) -> bool:
        if msg_id in self._seen:
            return False
        self._seen[msg_id] = None
        while len(self._seen) > 1000:
            self._seen.popitem(last=False)
        return True

    def _stream_once(self) -> bool:
        url = subscribe_url(self.url, self.topic, self.since)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/x-ndjson"})
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        log.info("connecting to %s (since=%s)", self.url, self.since or "new messages only")
        got_data = False
        with self._opener.open(req, timeout=self.read_timeout) as resp:
            for raw in resp:
                msg = parse_line(raw)
                if msg is None:
                    continue
                event = msg.get("event")
                if not got_data:
                    got_data = True
                    self._note_connected()
                if event == "open":
                    # Resume point if the link drops before any message arrives.
                    if self.since is None and msg.get("time"):
                        self.since = str(int(msg["time"]))
                    continue
                if event != "message":
                    continue   # keepalive, poll_request, ...
                msg_id = str(msg.get("id") or "")
                if msg_id:
                    self.since = msg_id
                    if not self._remember(msg_id):
                        continue
                self._dispatch(msg)
                if self.done:
                    return got_data
        return got_data

    def _dispatch(self, msg: dict) -> None:
        level = effective_level(msg, max_age_seconds=self.ring_max_age_seconds)
        if level is None:
            return
        if level != classify(msg):
            msg = dict(msg, _stale=True)
        log.info("alert id=%s priority=%s level=%s kind=%s title=%r", msg.get("id"), priority_of(msg), level,
                 kind_of(msg), _short(display_title(msg), 120))
        self.handled += 1
        try:
            self.handler(msg, level)
        except Exception:  # noqa: BLE001 - a bad handler must not kill the subscription
            log.exception("alert handler failed")


def read_stdin(handler: Handler, stop_event: threading.Event, stream: Any = None) -> int:
    """--stdin: messages in ntfy JSON format, one per line (used by newsalert's local mode)."""
    stream = stream if stream is not None else sys.stdin.buffer
    count = 0
    for raw in stream:
        if stop_event.is_set():
            break
        msg = parse_line(raw)
        level = classify(msg)
        if msg is None or level is None:
            continue
        count += 1
        try:
            handler(msg, level)
        except Exception:  # noqa: BLE001
            log.exception("alert handler failed")
    return count


# =========================================================================== process plumbing


def acquire_single_instance_lock(key: str) -> Optional[Any]:
    """Keep one listener per topic, so a login-started copy and a manual one don't both ring."""
    path = Path(tempfile.gettempdir()) / f"newsalert_listener_{hashlib.sha1(key.encode()).hexdigest()[:12]}.lock"
    try:
        fh = open(path, "a+")
    except OSError:
        return object()   # can't lock: run anyway rather than not at all
    try:
        if IS_WINDOWS:
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def sample_message(urgent: bool) -> dict:
    return {
        "id": "test",
        "time": int(time.time()),
        "event": "message",
        "topic": "test",
        "title": "[ANIME] [OFFICIAL SOURCE] TEST — Studio X announces Season 2 of Y",
        "message": ("Summary: This is a test alert. Studio X confirmed Season 2 of Y for July 2027.\n"
                    "Source: @StudioX_official (X) · 47s ago\n"
                    "Links: original post · Anime News Network"),
        "priority": 5 if urgent else 4,
        "tags": ["rotating_light", "na-test"] if urgent else ["na-test"],
        "click": "https://example.com/newsalert-test",
    }


def run_desktop(cfg: Config, source: Callable[[Handler, threading.Event, DesktopAlerter], Any],
                headless_ring_seconds: Optional[float] = None) -> int:
    """Run `source` (which feeds messages to the handler) with real sounds/window/toasts."""
    player = SoundPlayer(cfg.ring_sound, cfg.chime_sound)
    player.check_files()
    ui = make_ui(player, cfg.ring_timeout_seconds)
    on_fail = (lambda t, b, u: ui.call(ui.show_popup, t, b, u)) if ui is not None else None
    toaster = Toaster(on_failure=on_fail)
    alerter = DesktopAlerter(cfg, ui, player, toaster)
    if headless_ring_seconds is not None:
        alerter.headless_ring_seconds = headless_ring_seconds
    stop = threading.Event()
    finished = threading.Event()

    def worker() -> None:
        try:
            source(alerter.handle, stop, alerter)
        except Exception:  # noqa: BLE001
            log.exception("listener stopped by an error")
        finally:
            finished.set()

    try:
        if ui is None:
            worker()
            while alerter.busy:
                time.sleep(0.2)
            return 0
        threading.Thread(target=worker, name="source", daemon=True).start()
        try:   # Tk swallows KeyboardInterrupt inside callbacks, so make Ctrl+C quit explicitly
            import signal
            signal.signal(signal.SIGINT, lambda *_: ui.quit())
        except (ImportError, ValueError):
            pass

        def check_done() -> None:
            if finished.is_set() and not alerter.busy:
                ui.quit()
            else:
                ui.root.after(300, check_done)

        ui.root.after(300, check_done)
        ui.run()
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        stop.set()
        player.stop_ring()
        if ui is not None:
            ui.destroy()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="newsalert_listener",
        description="Ring this computer when your newsalert ntfy topic gets an urgent alert. Listens only; never posts.",
    )
    p.add_argument("--config", help="path to listener.ini (default: next to this file)")
    p.add_argument("--url", help=f"ntfy server (default {DEFAULT_URL})")
    p.add_argument("--topic", help="your ntfy topic (same as NTFY_TOPIC on the VM)")
    p.add_argument("--token", help="ntfy access token (better: put it in listener.ini)")
    p.add_argument("--sounds-dir", dest="sounds_dir", help="folder with ring.wav and chime.wav")
    p.add_argument("--ring-sound", dest="ring_sound", help=argparse.SUPPRESS)
    p.add_argument("--chime-sound", dest="chime_sound", help=argparse.SUPPRESS)
    p.add_argument("--log-file", dest="log_file", help="log file (default newsalert_listener.log next to this file; '-' = none)")
    p.add_argument("--test-ring", action="store_true", help="show a sample urgent alert and ring (no ntfy needed)")
    p.add_argument("--test-chime", action="store_true", help="play the chime and show a toast (no ntfy needed)")
    p.add_argument("--once", action="store_true", help="exit after the first alert (for testing)")
    p.add_argument("--stdin", action="store_true", help=argparse.SUPPRESS)   # local mode of newsalert itself
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _fatal(text: str, toast: bool) -> int:
    log.error(text)
    if toast:   # started with pythonw: the log file is the only other trace, so also pop a toast
        show_toast("newsalert listener could not start", text, None, "quiet")
    return 2


def main(argv: Optional[list[str]] = None, handler: Optional[Handler] = None) -> int:
    """Entry point. `handler` replaces sounds/window/toasts (tests use a stub)."""
    args = build_parser().parse_args(argv)
    cfg = load_config(args)
    setup_logging(cfg.log_file, args.verbose, (cfg.token,))
    no_console = sys.stderr is None

    if args.test_ring or args.test_chime:
        msg = sample_message(urgent=bool(args.test_ring))
        level = "urgent" if args.test_ring else "normal"
        log.info("test: %s (sounds from %s)", level, cfg.sounds_dir)
        if handler is not None:
            handler(msg, level)
            return 0
        print("Test alert shown. Press Open or Dismiss to stop the ring." if args.test_ring else "Chime played.")
        return run_desktop(cfg, lambda h, _stop, _a: h(msg, level), headless_ring_seconds=10.0)

    if args.stdin:
        if handler is not None:
            read_stdin(handler, threading.Event())
            return 0
        return run_desktop(cfg, lambda h, stop, _a: read_stdin(h, stop))

    if not cfg.topic:
        return _fatal("No topic set. Put 'topic = <your topic>' in listener.ini "
                           f"({SCRIPT_DIR / 'listener.ini'}) or pass --topic.", no_console)
    if not valid_topic(cfg.topic):
        return _fatal("The topic may only contain letters, digits, '-' and '_' (max 64). "
                           "Use the same value as NTFY_TOPIC on the VM.", no_console)
    if not cfg.url.lower().startswith(("http://", "https://")):
        return _fatal(f"The server url must start with https:// (got {cfg.url!r}).", no_console)

    lock = None
    if not args.once and handler is None:
        lock = acquire_single_instance_lock(f"{cfg.url}|{cfg.topic}")
        if lock is None:
            log.warning("another listener for this topic is already running on this computer; exiting")
            return 0

    log.info("newsalert listener %s starting: server %s, sounds %s, token %s", __version__, cfg.url,
             cfg.sounds_dir, "set" if cfg.token else "none")

    def subscribe(h: Handler, stop: threading.Event, alerter: Optional[DesktopAlerter]) -> int:
        sub = Subscriber(
            cfg.url, cfg.topic, cfg.token, h,
            stop_after=1 if args.once else None,
            stop_event=stop,
            ring_max_age_seconds=cfg.ring_max_age_seconds,
            on_status=alerter.on_status if alerter is not None else None,
        )
        return sub.run()

    try:
        if handler is not None:
            subscribe(handler, threading.Event(), None)
            return 0
        return run_desktop(cfg, subscribe)
    except KeyboardInterrupt:
        return 0
    finally:
        if lock is not None:
            lock.close()


if __name__ == "__main__":
    sys.exit(main())
