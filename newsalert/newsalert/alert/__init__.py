"""Alert data model shared by formatting (format.py) and delivery (ntfy.py, local.py).

Delivery never posts anywhere public: the only channels are the owner's own
ntfy topic and the local machine's sound/notification system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

AlertKind = Literal["ring", "followup", "retraction", "health", "test", "digest"]
# urgent = loud ring that repeats until dismissed (ntfy priority 5)
# normal = single chime (ntfy priority 4)
# quiet  = notification without sound (ntfy priority 2): follow-ups, muted alerts
Urgency = Literal["urgent", "normal", "quiet"]

NTFY_PRIORITY: dict[str, int] = {"urgent": 5, "normal": 4, "quiet": 2}


@dataclass
class Alert:
    kind: AlertKind
    urgency: Urgency
    title: str                      # e.g. "[ANIME] [OFFICIAL SOURCE] Studio X announces Season 2 of Y"
    message: str                    # multi-line body (summary, source line, links)
    click_url: str | None = None    # opened when the notification is clicked
    links: list[tuple[str, str]] = field(default_factory=list)  # (label, url), max 3 extra sources
    tags: list[str] = field(default_factory=list)               # ntfy tags / emoji shortcodes
    story_id: int | None = None

    @property
    def ntfy_priority(self) -> int:
        return NTFY_PRIORITY[self.urgency]


@dataclass
class DeliveryResult:
    ok: bool
    channel: str                    # "ntfy" | "local"
    error: str | None = None
    attempts: int = 1


class Notifier(Protocol):
    channel: str

    async def send(self, alert: Alert) -> DeliveryResult: ...
