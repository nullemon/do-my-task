"""Pick the delivery channels from ALERT_MODE and send each alert on all of them at once.

ALERT_MODE (from .env):
  ntfy  (default) POST to your ntfy topic; the laptop listener / phone app rings
  local           sound + notification on this machine
  both            both of the above
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx

from ..config import AppConfig
from . import Alert, DeliveryResult, Notifier
from .local import LocalNotifier
from .ntfy import DEFAULT_URL, TOPIC_RE, NtfyNotifier

log = logging.getLogger("newsalert.alert.delivery")

MODES = ("ntfy", "local", "both")
MIN_TOPIC_LENGTH = 16   # anyone who guesses the topic can read your alerts


def _ntfy_from_env(cfg: AppConfig, client: httpx.AsyncClient) -> NtfyNotifier | None:
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        log.error(
            "alert.ntfy_not_configured",
            extra={"hint": "NTFY_TOPIC is empty. Set NTFY_TOPIC in .env to a long random topic name "
                           "(the same one the laptop listener and phone app subscribe to; see "
                           "docs/laptop-setup.md). Falling back to local alerts on this machine."},
        )
        return None
    if not TOPIC_RE.match(topic):
        log.error(
            "alert.ntfy_not_configured",
            extra={"hint": "NTFY_TOPIC may only contain letters, digits, '-' and '_' (max 64 characters); "
                           "use just the topic name, not the URL. Falling back to local alerts on this machine."},
        )
        return None
    if len(topic) < MIN_TOPIC_LENGTH:
        log.warning("alert.ntfy_topic_short", extra={"length": len(topic),
                    "hint": "short topic names are guessable; use 20+ random characters"})
    a = cfg.settings.alerts
    return NtfyNotifier(
        client,
        topic=topic,
        url=os.environ.get("NTFY_URL", "").strip() or DEFAULT_URL,
        token=os.environ.get("NTFY_TOKEN", "").strip() or None,
        retries=a.ntfy_retries,
        retry_window=a.ntfy_retry_window_seconds,
    )


def build_notifiers(cfg: AppConfig, client: httpx.AsyncClient) -> list[Notifier]:
    mode = (os.environ.get("ALERT_MODE") or "ntfy").strip().lower()
    if mode not in MODES:
        log.error("alert.bad_mode", extra={"mode": mode, "hint": "ALERT_MODE must be ntfy, local or both; using ntfy"})
        mode = "ntfy"

    notifiers: list[Notifier] = []
    if mode in ("ntfy", "both"):
        ntfy = _ntfy_from_env(cfg, client)
        if ntfy is not None:
            notifiers.append(ntfy)
    if mode in ("local", "both") or not notifiers:
        notifiers.append(LocalNotifier.from_config(cfg))
    log.info("alert.channels", extra={"mode": mode, "channels": [n.channel for n in notifiers]})
    return notifiers


async def deliver(notifiers: list[Notifier], alert: Alert) -> list[DeliveryResult]:
    """Send on every channel concurrently. Never raises; failures come back as ok=False."""
    if not notifiers:
        log.error("alert.no_channels", extra={"title": alert.title})
        return []
    raw = await asyncio.gather(*(n.send(alert) for n in notifiers), return_exceptions=True)
    results: list[DeliveryResult] = []
    for notifier, res in zip(notifiers, raw):
        if isinstance(res, DeliveryResult):
            results.append(res)
            continue
        if isinstance(res, asyncio.CancelledError):
            raise res
        error = f"{type(res).__name__}: {res}"
        log.error("alert.delivery_failed", extra={"channel": notifier.channel, "error": error, "title": alert.title})
        results.append(DeliveryResult(ok=False, channel=notifier.channel, error=error))
    if not any(r.ok for r in results):
        log.error("alert.all_channels_failed", extra={
            "kind": alert.kind, "story_id": alert.story_id, "title": alert.title,
            "errors": {r.channel: r.error for r in results},
        })
    return results


def make_test_alert(urgent: bool) -> Alert:
    """A realistic sample in the final alert format, for `newsalert test-alert`."""
    links = [
        ("Anime News Network", "https://example.com/newsalert-test/ann"),
        ("Crunchyroll News", "https://example.com/newsalert-test/crunchyroll"),
    ]
    original = "https://example.com/newsalert-test/studiox-post"
    lines = [
        "Summary: TEST ALERT - Studio X confirmed a second season of Y for July 2027, "
        "with the original staff returning.",
        "Source: @StudioX_official (X) · 47s ago",
        "Links: original post · " + " · ".join(name for name, _ in links),
        *(f"  {name}: {url}" for name, url in links),
        f"  original: {original}",
    ]
    return Alert(
        kind="test",
        urgency="urgent" if urgent else "normal",
        title="[ANIME] [OFFICIAL SOURCE] TEST — Studio X announces Season 2 of Y",
        message="\n".join(lines),
        click_url=original,
        links=links,
        tags=["anime", "test_tube"],
    )
