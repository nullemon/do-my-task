"""Deliver alerts to the owner's ntfy topic (ntfy.sh by default).

JSON publishing: one POST to the server root with the topic in the body, so the
topic (which acts as a password) never appears in a URL or a log line. The same
messages work unchanged in the ntfy phone/web apps and in laptop/newsalert_listener.py.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Awaitable, Callable

import httpx

from . import Alert, DeliveryResult

log = logging.getLogger("newsalert.alert.ntfy")

DEFAULT_URL = "https://ntfy.sh"
MAX_ACTIONS = 3                 # ntfy rejects more than 3 actions
MAX_MESSAGE_BYTES = 3900        # ntfy.sh limit is 4096; longer bodies become attachments
MAX_TITLE_CHARS = 250
MAX_LABEL_CHARS = 40
ATTEMPT_TIMEOUT = 3.0           # seconds per HTTP attempt
RETRY_DELAYS = (0.5, 1.0, 2.0)  # pause before retry 1, 2, 3...
URGENT_TAG = "rotating_light"   # 🚨 in the ntfy apps
KIND_TAG_PREFIX = "na-"         # na-ring, na-followup, ... read by the laptop listener

TOPIC_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def kind_tag(kind: str) -> str:
    return f"{KIND_TAG_PREFIX}{kind}"


def _clean_tag(tag: str) -> str:
    # ntfy joins tags with commas internally, so a comma would split one tag in two.
    return tag.replace(",", " ").strip()


def _truncate_bytes(text: str, limit: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= limit:
        return text
    cut = raw[: limit - 3].decode("utf-8", errors="ignore").rstrip()
    return cut + "…"


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _is_web_url(url: str | None) -> bool:
    return bool(url) and url.lower().startswith(("http://", "https://"))


def build_tags(alert: Alert) -> list[str]:
    tags: list[str] = []
    if alert.urgency == "urgent":
        tags.append(URGENT_TAG)
    tags.extend(alert.tags)
    tags.append(kind_tag(alert.kind))
    out: list[str] = []
    for t in tags:
        t = _clean_tag(t)
        if t and t not in out:
            out.append(t)
    return out


def build_actions(alert: Alert) -> list[dict]:
    actions = []
    for label, url in alert.links:
        if not _is_web_url(url):
            continue
        actions.append({
            "action": "view",
            "label": _truncate(label or "Open", MAX_LABEL_CHARS),
            "url": url,
            "clear": False,
        })
        if len(actions) >= MAX_ACTIONS:
            break
    return actions


def ntfy_payload(alert: Alert, topic: str) -> dict:
    """The JSON body ntfy expects. Also what the laptop listener receives back (plus id/time/event)."""
    payload: dict = {
        "topic": topic,
        "title": _truncate(alert.title, MAX_TITLE_CHARS),
        "message": _truncate_bytes(alert.message or alert.title, MAX_MESSAGE_BYTES),
        "priority": alert.ntfy_priority,
        "tags": build_tags(alert),
        "actions": build_actions(alert),
    }
    if _is_web_url(alert.click_url):
        payload["click"] = alert.click_url
    return payload


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _error_text(resp: httpx.Response) -> str:
    # ntfy errors look like {"code":40101,"http":401,"error":"unauthorized",...}; never echo headers.
    try:
        data = resp.json()
        detail = data.get("error") if isinstance(data, dict) else None
    except ValueError:
        detail = None
    detail = detail or resp.text
    return f"HTTP {resp.status_code}: {_truncate(str(detail).strip(), 200)}"


class NtfyNotifier:
    channel = "ntfy"

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        topic: str,
        url: str = DEFAULT_URL,
        token: str | None = None,
        retries: int = 2,
        retry_window: float = 5.0,
        attempt_timeout: float = ATTEMPT_TIMEOUT,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._client = client
        self._topic = topic
        self._url = (url or DEFAULT_URL).rstrip("/") + "/"
        self._token = token or None
        self._retries = max(0, retries)
        self._window = max(0.0, retry_window)
        self._attempt_timeout = attempt_timeout
        self._sleep = sleep

    def payload(self, alert: Alert) -> dict:
        return ntfy_payload(alert, self._topic)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def send(self, alert: Alert) -> DeliveryResult:
        body = self.payload(alert)
        headers = self._headers()
        start = time.monotonic()
        attempts = 0
        error = "not attempted"
        status: int | None = None
        ctx = {"channel": self.channel, "kind": alert.kind, "urgency": alert.urgency, "story_id": alert.story_id}

        while True:
            attempts += 1
            elapsed = time.monotonic() - start
            timeout = self._attempt_timeout if attempts == 1 else max(0.5, min(self._attempt_timeout, self._window - elapsed))
            retryable = False
            wait_hint: float | None = None
            status = None
            try:
                resp = await self._client.post(self._url, json=body, headers=headers, timeout=timeout)
            except httpx.TransportError as exc:  # connect/read errors and timeouts
                error = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
                retryable = True
            except Exception as exc:  # bad URL, etc.: retrying won't help
                error = f"{type(exc).__name__}: {exc}"
            else:
                if resp.is_success:
                    ntfy_id = None
                    try:
                        data = resp.json()
                        ntfy_id = data.get("id") if isinstance(data, dict) else None
                    except ValueError:
                        pass
                    log.info("alert.delivered", extra={**ctx, "attempts": attempts, "ntfy_id": ntfy_id})
                    return DeliveryResult(ok=True, channel=self.channel, attempts=attempts)
                error = _error_text(resp)
                status = resp.status_code
                retryable = resp.status_code == 429 or resp.status_code >= 500
                if resp.status_code == 429:
                    wait_hint = _retry_after(resp)

            if not retryable or attempts > self._retries:
                break
            delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)]
            if wait_hint is not None:
                delay = max(delay, wait_hint)
            remaining = self._window - (time.monotonic() - start)
            if delay + 0.25 > remaining:   # no time left for a useful attempt
                break
            log.warning("alert.delivery_retry", extra={**ctx, "attempt": attempts, "error": error, "retry_in": delay})
            await self._sleep(delay)

        hint = ""
        if status in (401, 403):
            hint = "check NTFY_TOKEN, and that the token may write to this topic"
        elif status == 429:
            hint = "ntfy rate limit reached (the ntfy.sh free tier allows about 250 messages a day)"
        elif status is None:
            hint = "check that this machine can reach NTFY_URL over HTTPS"
        log.error(
            "alert.delivery_failed",
            extra={**ctx, "attempts": attempts, "error": error, "hint": hint or None, "title": alert.title},
        )
        return DeliveryResult(ok=False, channel=self.channel, error=error, attempts=attempts)
