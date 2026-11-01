"""Start all watcher loops and run until interrupted."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

import httpx

from .config import AppConfig, load_config
from .db import Database
from .log import setup_logging
from .pipeline import ConsoleSink, Pipeline
from .watchers import WatcherContext, build_watchers

log = logging.getLogger("newsalert.main")


def make_client(cfg: AppConfig) -> httpx.AsyncClient:
    p = cfg.settings.polling
    return httpx.AsyncClient(
        timeout=httpx.Timeout(p.request_timeout),
        follow_redirects=True,
        headers={"User-Agent": p.user_agent},
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )


async def run(cfg: AppConfig) -> None:
    db = Database(cfg.resolve(cfg.settings.db_path))
    sink = ConsoleSink()
    pipeline = Pipeline(db, cfg.settings, sink)

    async with make_client(cfg) as client:
        ctx = WatcherContext(db=db, pipeline=pipeline, client=client, settings=cfg.settings)
        watchers = build_watchers(cfg.sources, ctx)
        unseeded = [w.source.name for w in watchers if not db.get_source_state(w.source.name).get("seeded")]
        log.info(
            "newsalert.start",
            extra={
                "watchers": len(watchers),
                "watchlist_entries": len(cfg.watchlist.entries),
                "seeding_sources": len(unseeded),
            },
        )
        print(
            f"newsalert: watching {len(watchers)} sources "
            f"({len(cfg.watchlist.entries)} watchlist entries). "
            + (f"First poll of {len(unseeded)} source(s) marks existing items as seen without alerting. " if unseeded else "")
            + "Ctrl+C to stop.",
            flush=True,
        )

        tasks = [asyncio.create_task(w.run(), name=f"watch:{w.source.name}") for w in watchers]
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
