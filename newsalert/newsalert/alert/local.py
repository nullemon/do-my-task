"""Alerts on the machine newsalert runs on (ALERT_MODE=local or both).

  urgent -> ring.wav repeats until dismissed + a notification
  normal -> chime.wav once + a notification
  quiet  -> notification only

Windows: hands each alert to laptop/newsalert_listener.py running as a child process
(--stdin mode), so you get the same topmost Open/Dismiss window, stacking and toasts as
the laptop listener. Linux: notify-send + paplay/aplay. macOS: osascript + afplay.
On Linux/macOS the ring loops for up to ~2 minutes or until the notification/dialog is
dismissed (best effort). Nothing here blocks the event loop: every tool runs as a
subprocess. A missing tool logs a warning and never raises.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from . import Alert, DeliveryResult
from .ntfy import ntfy_payload

if TYPE_CHECKING:
    from ..config import AppConfig

log = logging.getLogger("newsalert.alert.local")

RING_MAX_SECONDS = 120.0
CREATE_NO_WINDOW = 0x08000000
_DEVNULL = asyncio.subprocess.DEVNULL
_PIPE = asyncio.subprocess.PIPE


def _short(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def listener_message(alert: Alert, msg_id: str) -> dict:
    """The alert as the ntfy server would stream it to a subscriber."""
    msg = ntfy_payload(alert, topic="local")
    msg.update(id=msg_id, time=int(time.time()), event="message")
    return msg


class LocalNotifier:
    channel = "local"

    def __init__(
        self,
        ring_sound: Path,
        chime_sound: Path,
        *,
        listener_script: Path | None = None,
        listener_log: Path | None = None,
        ring_max_seconds: float = RING_MAX_SECONDS,
        platform: str | None = None,
    ) -> None:
        self.ring_sound = Path(ring_sound)
        self.chime_sound = Path(chime_sound)
        self.listener_script = listener_script
        self.listener_log = listener_log
        self.ring_max_seconds = ring_max_seconds
        self.platform = platform or sys.platform
        self._ids = itertools.count(1)
        self._warned: set[str] = set()
        self._tasks: set[asyncio.Task] = set()
        # Windows child listener
        self._child: asyncio.subprocess.Process | None = None
        # POSIX ring state
        self._ring_task: asyncio.Task | None = None
        self._ring_stop: asyncio.Event | None = None
        self._ring_deadline = 0.0
        self._awaiting_dismiss = 0
        self._dialog_open = False

    @classmethod
    def from_config(cls, cfg: "AppConfig") -> "LocalNotifier":
        a = cfg.settings.alerts
        return cls(
            cfg.resolve(a.ring_sound),
            cfg.resolve(a.chime_sound),
            listener_script=cfg.root / "laptop" / "newsalert_listener.py",
            listener_log=cfg.resolve(cfg.settings.db_path).parent / "local-alerts.log",
        )

    @property
    def is_windows(self) -> bool:
        return self.platform == "win32"

    @property
    def is_mac(self) -> bool:
        return self.platform == "darwin"

    @property
    def ringing(self) -> bool:
        return self._ring_task is not None and not self._ring_task.done()

    # ------------------------------------------------------------------ helpers

    def _warn_once(self, key: str, event: str, **extra) -> None:
        if key in self._warned:
            return
        self._warned.add(key)
        log.warning(event, extra=extra)

    def _spawn_task(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _tool(self, name: str, hint: str) -> str | None:
        path = shutil.which(name)
        if path is None:
            self._warn_once(f"tool:{name}", "local.tool_missing", tool=name, hint=hint)
        return path

    async def _run(self, *cmd: str, timeout: float = 10.0, **kw) -> tuple[int | None, str]:
        """Run a short-lived tool; returns (returncode, stdout). Never raises."""
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdin=_DEVNULL, stdout=_PIPE, stderr=_DEVNULL, **kw)
        except OSError as exc:
            self._warn_once(f"run:{cmd[0]}", "local.tool_failed", tool=cmd[0], error=str(exc))
            return None, ""
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
            return None, ""
        return proc.returncode, (out or b"").decode("utf-8", "replace").strip()

    def _player_cmd(self, path: Path) -> list[str] | None:
        if not path.exists():
            self._warn_once(f"file:{path}", "local.sound_missing", path=str(path),
                            hint="run: python tools/make_sounds.py")
            return None
        if self.is_mac:
            exe = self._tool("afplay", "afplay ships with macOS")
            return [exe, str(path)] if exe else None
        for cmd in (["paplay"], ["pw-play"], ["aplay", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
            exe = shutil.which(cmd[0])
            if exe:
                return [exe, *cmd[1:], str(path)]
        self._warn_once("tool:player", "local.tool_missing", tool="paplay/aplay",
                        hint="install pulseaudio-utils or alsa-utils for sound")
        return None

    # ------------------------------------------------------------------ entry point

    async def send(self, alert: Alert) -> DeliveryResult:
        try:
            if self.is_windows:
                ok, error = await self._send_windows(alert)
            else:
                ok, error = await self._send_posix(alert)
        except Exception as exc:  # never let a local tool problem break delivery
            ok, error = False, f"{type(exc).__name__}: {exc}"
        extra = {"channel": self.channel, "kind": alert.kind, "urgency": alert.urgency, "story_id": alert.story_id}
        if ok:
            log.info("alert.delivered", extra=extra)
        else:
            log.error("alert.delivery_failed", extra={**extra, "error": error, "title": alert.title})
        return DeliveryResult(ok=ok, channel=self.channel, error=None if ok else error)

    async def wait_idle(self, timeout: float | None = None) -> None:
        """Wait until the ring and any open dismiss dialogs are finished (for short-lived
        commands like `newsalert test-alert`, so exiting doesn't cut the ring short)."""
        if self.is_windows:
            return   # the child listener keeps ringing on its own after we exit
        pending = [t for t in self._tasks if not t.done()]
        if pending:
            await asyncio.wait(pending, timeout=timeout)

    async def aclose(self) -> None:
        """Call on shutdown. Stops the Linux/macOS ring. On Windows it only closes the child
        listener's input: the child exits by itself once its ring window is dismissed."""
        self.stop_ring()
        for task in list(self._tasks):
            task.cancel()
        child, self._child = self._child, None
        if child is not None and child.returncode is None:
            with contextlib.suppress(Exception):
                child.stdin.close()

    # ------------------------------------------------------------------ Windows

    async def _ensure_child(self) -> asyncio.subprocess.Process | None:
        if self._child is not None and self._child.returncode is None:
            return self._child
        script = self.listener_script
        if script is None or not script.exists():
            self._warn_once("listener", "local.listener_missing", path=str(script),
                            hint="laptop/newsalert_listener.py gives the ring window; falling back to sound only")
            return None
        cmd = [sys.executable, str(script), "--stdin", "--ring-sound", str(self.ring_sound),
               "--chime-sound", str(self.chime_sound), "--log-file", str(self.listener_log or "-")]
        flags = {"creationflags": CREATE_NO_WINDOW} if sys.platform == "win32" else {}   # no console window
        try:
            self._child = await asyncio.create_subprocess_exec(
                *cmd, stdin=_PIPE, stdout=_DEVNULL, stderr=_DEVNULL, **flags,
            )
        except (OSError, ValueError) as exc:
            self._warn_once("listener-start", "local.listener_failed", error=str(exc))
            return None
        log.info("local.listener_started", extra={"pid": self._child.pid})
        return self._child

    async def _send_windows(self, alert: Alert) -> tuple[bool, str | None]:
        line = (json.dumps(listener_message(alert, f"local-{next(self._ids)}"), ensure_ascii=True) + "\n").encode()
        for _ in range(2):   # one restart if the child died
            child = await self._ensure_child()
            if child is None:
                break
            try:
                child.stdin.write(line)
                await child.stdin.drain()
                return True, None
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                log.warning("local.listener_restart", extra={"error": str(exc)})
                with contextlib.suppress(ProcessLookupError):
                    child.kill()
                self._child = None
        return self._windows_sound_only(alert)

    def _windows_sound_only(self, alert: Alert) -> tuple[bool, str | None]:
        try:
            import winsound  # type: ignore[import-not-found]
        except ImportError:
            return False, "winsound unavailable"
        if alert.urgency == "quiet":
            return False, "no notification channel available (listener missing)"
        flags = winsound.SND_FILENAME | winsound.SND_ASYNC
        path = self.ring_sound if alert.urgency == "urgent" else self.chime_sound
        if alert.urgency == "urgent":
            flags |= winsound.SND_LOOP
            asyncio.get_running_loop().call_later(self.ring_max_seconds, winsound.PlaySound, None, 0)
        winsound.PlaySound(str(path), flags)
        return True, None

    # ------------------------------------------------------------------ Linux / macOS

    async def _send_posix(self, alert: Alert) -> tuple[bool, str | None]:
        title = _short(alert.title, 200)
        body = _short(alert.message, 400)
        shown = await self._notify(alert, title, body)
        sounded = False
        if alert.urgency == "urgent":
            sounded = self.start_ring()
        elif alert.urgency == "normal" and not self.ringing:
            sounded = await self._play_once(self.chime_sound)
        if shown or sounded:
            return True, None
        return False, "no notification tool or sound player worked"

    async def _notify(self, alert: Alert, title: str, body: str) -> bool:
        if self.is_mac:
            return await self._notify_mac(alert, title, body)
        exe = self._tool("notify-send", "install libnotify-bin for desktop notifications")
        if exe is None:
            return False
        level = {"urgent": "critical", "normal": "normal"}.get(alert.urgency, "low")
        base = [exe, "-a", "newsalert", "-u", level]
        if alert.urgency == "urgent":
            # --wait + actions: the notify-send exits when the owner clicks or closes it -> stop ring.
            try:
                proc = await asyncio.create_subprocess_exec(
                    *base, "--action=open=Open", "--action=dismiss=Dismiss", "--wait", "--", title, body,
                    stdin=_DEVNULL, stdout=_PIPE, stderr=_DEVNULL,
                )
            except OSError as exc:
                self._warn_once("run:notify-send", "local.tool_failed", tool="notify-send", error=str(exc))
                return False
            comm = asyncio.ensure_future(proc.communicate())
            done, _ = await asyncio.wait({comm}, timeout=0.5)
            if not done:   # still waiting for the owner: it is on screen
                self._awaiting_dismiss += 1
                self._spawn_task(self._wait_dismiss(comm, alert.click_url))
                return True
            out, _ = comm.result()
            if proc.returncode == 0:   # closed already, or shown by a server that doesn't keep it
                self._handle_choice((out or b"").decode().strip(), alert.click_url)
                return True
            # older notify-send without --action/--wait: plain notification, ring runs to its time limit
        rc, _ = await self._run(*base, "--", title, body)
        return rc == 0

    async def _wait_dismiss(self, comm: asyncio.Future, url: str | None) -> None:
        try:
            out, _ = await comm
            self._handle_choice((out or b"").decode().strip(), url)
        finally:
            self._awaiting_dismiss = max(0, self._awaiting_dismiss - 1)
            if self._awaiting_dismiss == 0:
                self.stop_ring()

    def _handle_choice(self, choice: str, url: str | None) -> None:
        if choice.lower() == "open" and url and url.startswith(("http://", "https://")):
            opener = "open" if self.is_mac else "xdg-open"
            if shutil.which(opener):
                self._spawn_task(self._run(opener, url))

    async def _notify_mac(self, alert: Alert, title: str, body: str) -> bool:
        exe = self._tool("osascript", "osascript ships with macOS")
        if exe is None:
            return False
        script = ["-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
                  "-e", "end run"]
        rc, _ = await self._run(exe, *script, title, body)
        if alert.urgency == "urgent" and not self._dialog_open:
            self._dialog_open = True
            self._awaiting_dismiss += 1
            self._spawn_task(self._mac_dialog(exe, title, body, alert.click_url))
        return rc == 0

    async def _mac_dialog(self, exe: str, title: str, body: str, url: str | None) -> None:
        give_up = int(self.ring_max_seconds)
        rc: int | None = None
        script = [
            "-e", "on run argv",
            "-e", 'set r to display dialog (item 2 of argv) with title (item 1 of argv) '
                  f'buttons {{"Dismiss", "Open"}} default button "Open" giving up after {give_up}',
            "-e", "return button returned of r",
            "-e", "end run",
        ]
        try:
            rc, out = await self._run(exe, *script, "newsalert - URGENT", f"{title}\n\n{body}", timeout=give_up + 10)
            if rc == 0:
                self._handle_choice(out, url)
        finally:
            self._dialog_open = False
            self._awaiting_dismiss = max(0, self._awaiting_dismiss - 1)
            if self._awaiting_dismiss == 0 and rc == 0:
                self.stop_ring()

    async def _play_once(self, path: Path) -> bool:
        cmd = self._player_cmd(path)
        if cmd is None:
            return False
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdin=_DEVNULL, stdout=_DEVNULL, stderr=_DEVNULL)
        except OSError as exc:
            self._warn_once("run:player", "local.tool_failed", tool=cmd[0], error=str(exc))
            return False
        self._spawn_task(proc.wait())
        return True

    def start_ring(self) -> bool:
        cmd = self._player_cmd(self.ring_sound)
        if cmd is None:
            return False
        loop = asyncio.get_running_loop()
        self._ring_deadline = loop.time() + self.ring_max_seconds   # a new urgent alert extends the ring
        if self.ringing:
            return True
        self._ring_stop = asyncio.Event()
        self._ring_task = self._spawn_task(self._ring_loop(cmd, self._ring_stop))
        return True

    def stop_ring(self) -> None:
        if self._ring_stop is not None:
            self._ring_stop.set()

    async def _ring_loop(self, cmd: list[str], stop: asyncio.Event) -> None:
        loop = asyncio.get_running_loop()
        failures = 0
        while not stop.is_set() and loop.time() < self._ring_deadline:
            started = loop.time()
            try:
                proc = await asyncio.create_subprocess_exec(*cmd, stdin=_DEVNULL, stdout=_DEVNULL, stderr=_DEVNULL)
            except OSError as exc:
                self._warn_once("run:player", "local.tool_failed", tool=cmd[0], error=str(exc))
                return
            waiter = asyncio.ensure_future(proc.wait())
            stopper = asyncio.ensure_future(stop.wait())
            try:
                await asyncio.wait({waiter, stopper}, timeout=max(0.1, self._ring_deadline - loop.time()),
                                   return_when=asyncio.FIRST_COMPLETED)
            finally:
                stopper.cancel()
                if not waiter.done():
                    with contextlib.suppress(ProcessLookupError):
                        proc.kill()
                    await waiter
            if proc.returncode not in (0, None) and loop.time() - started < 0.3:
                failures += 1
                if failures >= 3:
                    self._warn_once("player-fail", "local.sound_failed", tool=cmd[0],
                                    hint="the sound player keeps failing (no audio device?)")
                    return
                await asyncio.sleep(1.0)
            else:
                failures = 0
