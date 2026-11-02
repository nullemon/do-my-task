"""Watcher health: alert (normal priority) when a source has failed for 10+ minutes.

One alert per failure episode; a source that recovers and fails again alerts again.
Also writes a heartbeat that `newsalert healthcheck` (Docker HEALTHCHECK) reads.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable

from .alert.format import health_alert
from .config import AppConfig
from .db import Database

log = logging.getLogger("newsalert.health")

HEARTBEAT_KEY = "heartbeat"


class HealthMonitor:
    def __init__(self, db: Database, cfg: AppConfig, dispatcher, *, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.cfg = cfg
        self.dispatcher = dispatcher
        self.clock = clock

    async def run(self) -> None:
        interval = self.cfg.settings.health.check_interval_seconds
        while True:
            try:
                await self.check()
            except Exception:
                log.exception("health.check_failed")
            await asyncio.sleep(interval)

    async def check(self) -> list[str]:
        """Returns names of sources alerted on this round."""
        now = self.clock()
        self.db.kv_set(HEARTBEAT_KEY, str(now))
        limit = self.cfg.settings.health.failure_alert_minutes * 60
        alerted = []
        for source in self.cfg.enabled_sources:
            state = self.db.get_source_state(source.name)
            since = state.get("failing_since")
            key = f"health_alerted:{source.name}"
            if not since:
                if self.db.kv_get(key):
                    self.db.kv_set(key, None)  # recovered: re-arm
                continue
            if now - since < limit or self.db.kv_get(key) == repr(since):
                continue
            self.db.kv_set(key, repr(since))
            alerted.append(source.name)
            log.warning("health.source_failing", extra={"source": source.name, "minutes": round((now - since) / 60)})
            await self.dispatcher.submit(health_alert(source.name, (now - since) / 60, state.get("last_error")))
        return alerted
