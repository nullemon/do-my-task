"""Start watchers, the alert engine, the dispatcher and the health monitor."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

import httpx

from .alert.dispatch import Dispatcher
from .config import AppConfig, load_config
from .db import Database
from .engine import AlertEngine
from .health import HealthMonitor
from .log import setup_logging
from .pipeline import Pipeline
from .triage import HaikuTriager, NoAITriager
from .watchers import WatcherContext, build_watchers
from .watchlist import WatchlistIndex

log = logging.getLogger("newsalert.main")


def make_client(cfg: AppConfig) -> httpx.AsyncClient:
    p = cfg.settings.polling
    return httpx.AsyncClient(
        timeout=httpx.Timeout(p.request_timeout),
        follow_redirects=True,
        headers={"User-Agent": p.user_agent},
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )


def make_triager(cfg: AppConfig, db: Database):
    if HaikuTriager.available():
        return HaikuTriager(cfg.settings.triage, db)
    log.warning("triage.disabled", extra={
        "reason": "ANTHROPIC_API_KEY not set: every new item alerts on its raw headline, unfiltered",
    })
    return NoAITriager()


def build_stack(cfg: AppConfig, db: Database, client: httpx.AsyncClient, *, notifiers=None, triager=None):
    """Wire engine + dispatcher + pipeline. Shared by `run` and `replay`."""
    from .alert.delivery import build_notifiers, deliver

    if notifiers is None:
        notifiers = build_notifiers(cfg, client)
    index = WatchlistIndex(cfg.watchlist)
    engine = AlertEngine(db, cfg, triager or make_triager(cfg, db), index)
    dispatcher = Dispatcher(
        db, cfg.settings, send=lambda alert: deliver(notifiers, alert), build_story_alert=engine.build_ring_alert,
    )
    engine.dispatcher = dispatcher
    pipeline = Pipeline(db, cfg.settings, engine)
    return pipeline, engine, dispatcher, notifiers


async def run(cfg: AppConfig) -> None:
    db = Database(cfg.resolve(cfg.settings.db_path))
    async with make_client(cfg) as client:
        pipeline, engine, dispatcher, notifiers = build_stack(cfg, db, client)
        ctx = WatcherContext(
            db=db, pipeline=pipeline, client=client, settings=cfg.settings, watchlist=cfg.watchlist
        )
        watchers = build_watchers(cfg.sources, ctx)
        unseeded = [s.name for s in cfg.enabled_sources if not db.get_source_state(s.name).get("seeded")]
        restored = dispatcher.restore()
        log.info("newsalert.start", extra={
            "watchers": len(watchers), "watchlist_entries": len(cfg.watchlist.entries),
            "seeding_sources": len(unseeded), "channels": [n.channel for n in notifiers],
            "restored_queue": restored,
        })
        print(
            f"newsalert: {len(watchers)} watchers, {len(cfg.watchlist.entries)} watchlist entries, "
            f"alerts via {', '.join(n.channel for n in notifiers) or 'NOTHING (check ALERT_MODE / NTFY_TOPIC)'}. "
            + (f"First poll of {len(unseeded)} source(s) marks existing items as seen without alerting. " if unseeded else "")
            + "Ctrl+C to stop.",
            flush=True,
        )

        health = HealthMonitor(db, cfg, dispatcher)
        tasks = [asyncio.create_task(w.run(), name=f"watch:{w.name}") for w in watchers]
        tasks += [
            asyncio.create_task(dispatcher.run(), name="dispatch"),
            asyncio.create_task(dispatcher.run_flusher(), name="dispatch:flush"),
            asyncio.create_task(health.run(), name="health"),
        ]
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError, RuntimeError):  # Windows
                loop.add_signal_handler(sig, stop.set)
        try:
            await stop.wait()
        finally:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await engine.drain()
            for n in notifiers:
                if hasattr(n, "aclose"):
                    with contextlib.suppress(Exception):
                        await n.aclose()
            db.close()
            log.info("newsalert.stop")


def main() -> None:
    cfg = load_config()
    log_file = cfg.resolve(cfg.settings.log_file) if cfg.settings.log_file else None
    setup_logging(cfg.settings.log_level, log_file)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
