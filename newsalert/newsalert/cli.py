"""Command line: newsalert <command>.

Step 1 commands: run, check-sources, items.
Later steps add: test-alert, replay, mute, unmute, stats.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from .config import ConfigError, load_config
from .text import humanize_age, truncate


def _cmd_run(args: argparse.Namespace) -> int:
    from .main import main as run_main

    run_main()
    return 0


async def _check_sources(name_filter: str | None) -> int:
    from .main import make_client
    from .watchers.rss import fetch_feed

    cfg = load_config()
    sources = [
        s for s in cfg.sources
        if s.type == "rss" and (not name_filter or name_filter.lower() in s.name.lower())
    ]
    if not sources:
        print("no matching rss sources")
        return 1

    async with make_client(cfg) as client:
        async def one(src):
            t0 = time.monotonic()
            try:
                result = await fetch_feed(client, src)
                return src, result, None, time.monotonic() - t0
            except Exception as exc:  # report, don't crash
                return src, None, exc, time.monotonic() - t0

        results = await asyncio.gather(*(one(s) for s in sources))

    failed = 0
    now = time.time()
    stale_after = cfg.settings.pipeline.stale_minutes * 60
    for src, result, exc, elapsed in results:
        flag = "" if src.enabled else " (disabled)"
        if exc is not None:
            failed += 1
            print(f"FAIL  {src.name}{flag}: {type(exc).__name__}: {exc}"[:240])
            continue
        dated = [i.published_at for i in result.items if i.published_at]
        newest = now - max(dated) if dated else None
        validators = "etag" if result.state.get("etag") else ""
        if result.state.get("last_modified"):
            validators = f"{validators}+last-modified".strip("+")
        note = ""
        if newest is not None and newest < -300:
            note = "  <- newest item is dated in the FUTURE: feed time zone is probably wrong"
        elif newest is not None and newest > 6 * 3600:
            note = "  <- newest item is old: feed may be stale or mis-dated"
        elif not dated and result.items:
            note = "  <- items have no dates"
        print(
            f"OK    {src.name}{flag}: {len(result.items)} items, newest {humanize_age(newest)}, "
            f"{elapsed * 1000:.0f} ms, conditional GET: {validators or 'none'}{note}"
        )
    print(f"\n{len(results) - failed}/{len(results)} sources OK. Items older than {stale_after // 60} min on fetch are never alerted.")
    return 1 if failed else 0


def _cmd_check_sources(args: argparse.Namespace) -> int:
    return asyncio.run(_check_sources(args.name))


def _cmd_items(args: argparse.Namespace) -> int:
    from .db import Database

    cfg = load_config()
    db = Database(cfg.resolve(cfg.settings.db_path))
    now = time.time()
    counts = db.item_counts()
    print("items by status:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none")
    for row in reversed(db.recent_items(args.limit, status=args.status)):
        age = None if row["published_at"] is None else now - row["published_at"]
        print(f"{row['status']:7} [{row['category']}] {row['source']} · {humanize_age(age)} · {truncate(row['title'], 110)}")
    db.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="newsalert", description="Breaking-news alerts (alert only, never posts).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="start all watchers").set_defaults(func=_cmd_run)

    p = sub.add_parser("check-sources", help="fetch every RSS source once and report status")
    p.add_argument("--name", help="only sources whose name contains this text")
    p.set_defaults(func=_cmd_check_sources)

    p = sub.add_parser("items", help="show recently stored items")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--status", choices=["new", "seeded", "stale"])
    p.set_defaults(func=_cmd_items)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"config error:\n{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
