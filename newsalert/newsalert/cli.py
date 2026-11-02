"""Command line: newsalert <command>.

  run              start all watchers and alerting
  check-sources    fetch every RSS/YouTube feed once and report status
  items            show recently stored raw items
  test-alert       send a test alert (--urgent rings until dismissed, --normal chimes)
  replay FILE      replay recorded items through the full pipeline
  mute 30m|2h|1d   nothing rings until then (alerts still arrive silently)
  unmute
  stats            latency per source (median/p95), alerts sent, AI token cost
  healthcheck      exit 0 if the running process wrote a heartbeat recently (Docker)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

from .config import ConfigError, load_config
from .text import humanize_age, truncate


def _db(cfg):
    from .db import Database

    return Database(cfg.resolve(cfg.settings.db_path))


# --------------------------------------------------------------------------- run / sources / items


def _cmd_run(args: argparse.Namespace) -> int:
    from .main import main as run_main

    run_main()
    return 0


async def _check_sources(name_filter: str | None) -> int:
    from .main import make_client
    from .watchers.rss import fetch_feed

    cfg = load_config()
    sources = []
    for s in cfg.sources:
        if s.type not in ("rss", "youtube") or (name_filter and name_filter.lower() not in s.name.lower()):
            continue
        if s.type == "youtube" and not s.url:
            s = s.model_copy(update={"url": cfg.settings.youtube.feed_url_template.format(channel_id=s.account)})
        sources.append(s)
    if not sources:
        print("no matching rss/youtube sources")
        return 1

    async with make_client(cfg) as client:
        async def one(src):
            t0 = time.monotonic()
            try:
                return src, await fetch_feed(client, src), None, time.monotonic() - t0
            except Exception as exc:  # report, don't crash
                return src, None, exc, time.monotonic() - t0

        results = await asyncio.gather(*(one(s) for s in sources))

    failed = 0
    now = time.time()
    for src, result, exc, elapsed in results:
        flag = "" if src.enabled else " (disabled)"
        if exc is not None:
            failed += 1
            print(f"FAIL  {src.name}{flag}: {type(exc).__name__}: {exc}"[:240])
            continue
        dated = [i.published_at for i in result.items if i.published_at]
        newest = now - max(dated) if dated else None
        validators = "+".join(k for k in ("etag", "last_modified") if result.state.get(k)) or "none"
        note = ""
        if newest is not None and newest < -300:
            note = "  <- newest item is dated in the FUTURE: feed time zone is probably wrong"
        elif newest is not None and newest > 6 * 3600:
            note = "  <- newest item is old: feed may be stale or mis-dated"
        elif not dated and result.items:
            note = "  <- items have no dates"
        print(f"OK    {src.name}{flag}: {len(result.items)} items, newest {humanize_age(newest)}, "
              f"{elapsed * 1000:.0f} ms, conditional GET: {validators}{note}")
    stale = cfg.settings.pipeline.stale_minutes
    print(f"\n{len(results) - failed}/{len(results)} sources OK. Items older than {stale} min on fetch are never alerted.")
    return 1 if failed else 0


def _cmd_check_sources(args: argparse.Namespace) -> int:
    return asyncio.run(_check_sources(args.name))


def _cmd_items(args: argparse.Namespace) -> int:
    cfg = load_config()
    db = _db(cfg)
    now = time.time()
    counts = db.item_counts()
    print("items by status:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none")
    for row in reversed(db.recent_items(args.limit, status=args.status)):
        age = None if row["published_at"] is None else now - row["published_at"]
        print(f"{row['status']:7} [{row['category']}] {row['source']} · {humanize_age(age)} · {truncate(row['title'], 110)}")
    db.close()
    return 0


# --------------------------------------------------------------------------- test-alert


async def _test_alert(urgent: bool) -> int:
    from .alert.delivery import build_notifiers, deliver, make_test_alert
    from .main import make_client

    cfg = load_config()
    async with make_client(cfg) as client:
        notifiers = build_notifiers(cfg, client)
        if not notifiers:
            print("No alert channel configured. Set NTFY_TOPIC (and ALERT_MODE) in .env.", file=sys.stderr)
            return 1
        alert = make_test_alert(urgent)
        results = await deliver(notifiers, alert)
        for n in notifiers:  # local mode: let the ring play until dismissed before exiting
            if hasattr(n, "wait_idle"):
                await n.wait_idle(150)
            if hasattr(n, "aclose"):
                await n.aclose()
    db = _db(cfg)
    for r in results:
        db.record_alert(story_id=None, kind="test", urgency=alert.urgency, title=alert.title,
                        message=alert.message, channel=r.channel, ok=r.ok, error=r.error)
        print(f"{'OK  ' if r.ok else 'FAIL'} {r.channel}" + (f": {r.error}" if r.error else "")
              + (f" (after {r.attempts} attempts)" if r.attempts > 1 else ""))
    db.close()
    if any(r.ok for r in results):
        print("Sent. " + ("Your laptop should ring until you press Dismiss." if urgent else "Your laptop should chime once."))
    return 0 if any(r.ok for r in results) else 1


def _cmd_test_alert(args: argparse.Namespace) -> int:
    return asyncio.run(_test_alert(urgent=not args.normal))


# --------------------------------------------------------------------------- replay


async def _replay(path: Path, *, send: bool, no_ai: bool, realtime: bool) -> int:
    from .alert import DeliveryResult
    from .db import Database
    from .main import build_stack, make_client
    from .models import RawItem
    from .triage import NoAITriager

    cfg = load_config()
    data = json.loads(path.read_text(encoding="utf-8"))
    events = data["items"] if isinstance(data, dict) else data
    by_name = {s.name: s for s in cfg.sources}
    # Replay never dedupes against (or pollutes) the real database, and doesn't wait for spacing/quiet hours.
    settings = cfg.settings.model_copy(deep=True)
    settings.alerts.normal_min_gap_seconds = 0
    settings.quiet_hours.enabled = False
    cfg = cfg.model_copy(update={"settings": settings})

    class PrintOnly:
        channel = "dry-run"

        async def send(self, alert):
            return DeliveryResult(ok=True, channel=self.channel)

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "replay.db")
        async with make_client(cfg) as client:
            notifiers = None if send else [PrintOnly()]
            pipeline, engine, dispatcher, _ = build_stack(
                cfg, db, client, notifiers=notifiers, triager=NoAITriager() if no_ai else None,
            )
            async def settle():
                await engine.drain()
                while not dispatcher._queue.empty():
                    await dispatcher.process_one()

            start = time.monotonic()
            for ev in sorted(events, key=lambda e: e.get("at_s", 0)):
                if realtime:
                    await asyncio.sleep(max(0.0, ev.get("at_s", 0) - (time.monotonic() - start)))
                if "retract" in ev:
                    r = ev["retract"]
                    await pipeline.retract(r["source"], r["external_id"], r.get("reason", "deleted"))
                    await settle()
                    continue
                src = by_name.get(ev["source"])
                now = time.time()
                fields = {
                    "source": ev["source"],
                    "source_type": ev.get("source_type") or (src.type if src else "rss"),
                    "category": ev.get("category") or (src.category if src else "celebrity"),
                    "trust": ev.get("trust") or (src.trust if src else "major"),
                    "source_group": ev.get("group") or (src.independence_group if src else ev["source"]),
                    "url": ev.get("url"), "account": ev.get("account"),
                    "external_id": ev.get("external_id") or ev.get("url"),
                    "title": ev["title"], "text": ev.get("text") or ev["title"],
                    "published_at": now - ev.get("published_ago_s", 30), "fetched_at": now,
                }
                item = RawItem(**fields)
                source = src or _adhoc_source(item)
                await pipeline.ingest(source, [item], seeding=False)
                await settle()
        rows = db.conn.execute("SELECT kind, urgency, COUNT(*) n FROM alerts GROUP BY kind, urgency").fetchall()
        stories = db.conn.execute("SELECT status, COUNT(*) n FROM stories GROUP BY status").fetchall()
        db.close()
    print("\nreplay done: alerts " + (", ".join(f"{r['kind']}/{r['urgency']}={r['n']}" for r in rows) or "none")
          + " · stories " + ", ".join(f"{r['status']}={r['n']}" for r in stories))
    return 0


def _adhoc_source(item):
    from .config import Source

    return Source(name=item.source, type=item.source_type, url=item.url or "https://example.invalid",
                  account=item.account or "replay", category=item.category, trust=item.trust, group=item.source_group)


def _cmd_replay(args: argparse.Namespace) -> int:
    return asyncio.run(_replay(Path(args.fixture), send=args.send, no_ai=args.no_ai, realtime=args.realtime))


# --------------------------------------------------------------------------- mute


_DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s*([smhd]?)$")


def parse_duration(text: str) -> float:
    m = _DURATION.match(text.strip().lower())
    if not m:
        raise argparse.ArgumentTypeError(f"bad duration {text!r}; use e.g. 30m, 2h, 1d")
    value, unit = float(m.group(1)), m.group(2) or "m"
    return value * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


def _cmd_mute(args: argparse.Namespace) -> int:
    from .alert.dispatch import MUTE_KEY

    cfg = load_config()
    db = _db(cfg)
    until = time.time() + args.duration
    db.kv_set(MUTE_KEY, str(until))
    db.audit("mute", until=until)
    db.close()
    print(f"Muted until {time.strftime('%Y-%m-%d %H:%M', time.localtime(until))}. "
          "Nothing will ring; alerts still arrive silently. `newsalert unmute` to undo.")
    return 0


def _cmd_unmute(args: argparse.Namespace) -> int:
    from .alert.dispatch import MUTE_KEY

    cfg = load_config()
    db = _db(cfg)
    db.kv_set(MUTE_KEY, None)
    db.audit("unmute")
    db.close()
    print("Unmuted.")
    return 0


# --------------------------------------------------------------------------- stats


def _pct(values: list[float], p: float) -> float:
    vals = sorted(values)
    k = (len(vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def _dur(s: float | None) -> str:
    if s is None:
        return "-"
    if s < 60:
        return f"{s:.1f}s"
    return f"{int(s // 60)}m{int(s % 60):02d}s"


def stats_report(db, hours: float = 24, now: float | None = None) -> str:
    now = now or time.time()
    since = now - hours * 3600
    out = [f"newsalert stats — last {hours:g}h"]

    rows = db.conn.execute(
        """SELECT i.source, s.published_at, s.fetched_at, s.triaged_at, s.alerted_at
           FROM stories s JOIN items i ON i.id = s.first_item_id
           WHERE s.alerted_at >= ? AND s.status = 'alerted'""",
        (since,),
    ).fetchall()
    per: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        d = per.setdefault(r["source"], {"e2e": [], "pipe": []})
        if r["published_at"]:
            d["e2e"].append(max(0.0, r["alerted_at"] - r["published_at"]))
        d["pipe"].append(max(0.0, r["alerted_at"] - r["fetched_at"]))
    out.append("\nLatency per source (published → alerted; fetched → alerted)")
    if not per:
        out.append("  no alerted stories yet")
    else:
        out.append(f"  {'source':34} {'alerts':>6} {'median':>8} {'p95':>8} {'fetch→alert':>12}")
        for name, d in sorted(per.items(), key=lambda kv: -len(kv[1]["pipe"])):
            e2e = d["e2e"]
            out.append(
                f"  {truncate(name, 34):34} {len(d['pipe']):>6} "
                f"{_dur(statistics.median(e2e)) if e2e else '-':>8} {_dur(_pct(e2e, .95)) if e2e else '-':>8} "
                f"{_dur(statistics.median(d['pipe'])):>12}"
            )

    alerts = db.conn.execute(
        "SELECT kind, urgency, ok, COUNT(*) n FROM alerts WHERE created_at >= ? GROUP BY kind, urgency, ok", (since,)
    ).fetchall()
    sent = {}
    failed = 0
    for a in alerts:
        if a["ok"]:
            sent[f"{a['kind']}/{a['urgency']}"] = sent.get(f"{a['kind']}/{a['urgency']}", 0) + a["n"]
        else:
            failed += a["n"]
    out.append("\nAlerts delivered (per channel): " + (", ".join(f"{k}={v}" for k, v in sorted(sent.items())) or "none")
               + f"; failed deliveries: {failed}")

    st = db.conn.execute("SELECT status, COUNT(*) n FROM stories WHERE created_at >= ? GROUP BY status", (since,)).fetchall()
    out.append("Stories: " + (", ".join(f"{r['status']}={r['n']}" for r in st) or "none"))

    u = db.conn.execute(
        """SELECT COUNT(*) calls, COALESCE(SUM(ok),0) ok, COALESCE(SUM(input_tokens),0) inp,
                  COALESCE(SUM(output_tokens),0) outp, COALESCE(SUM(cost_usd),0) cost,
                  AVG(latency_ms) lat FROM usage WHERE ts >= ?""",
        (since,),
    ).fetchone()
    total = db.conn.execute("SELECT COALESCE(SUM(cost_usd),0) c FROM usage").fetchone()["c"]
    lat = f", avg {u['lat']:.0f} ms" if u["lat"] else ""
    out.append(f"Anthropic: {u['calls']} calls ({u['ok']} ok{lat}), {u['inp']:,} in / {u['outp']:,} out tokens, "
               f"${u['cost']:.4f} (all time ${total:.4f})")

    failing = [r for r in db.all_source_states() if r["failing_since"]]
    if failing:
        out.append("Watchers failing now: " + ", ".join(
            f"{r['source']} ({humanize_age(now - r['failing_since']).replace(' ago', '')}: {r['last_error']})" for r in failing))
    else:
        out.append("Watchers failing now: none")
    from .alert.dispatch import MUTE_KEY

    mute = db.kv_get(MUTE_KEY)
    if mute and float(mute) > now:
        out.append(f"Muted until {time.strftime('%Y-%m-%d %H:%M', time.localtime(float(mute)))}")
    return "\n".join(out)


def _cmd_stats(args: argparse.Namespace) -> int:
    cfg = load_config()
    db = _db(cfg)
    print(stats_report(db, args.hours))
    db.close()
    return 0


def _cmd_healthcheck(args: argparse.Namespace) -> int:
    from .health import HEARTBEAT_KEY

    cfg = load_config()
    db = _db(cfg)
    beat = db.kv_get(HEARTBEAT_KEY)
    db.close()
    age = time.time() - float(beat) if beat else None
    ok = age is not None and age < args.max_age
    print(f"heartbeat {humanize_age(age)}" if age is not None else "no heartbeat yet")
    return 0 if ok else 1


# --------------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="newsalert", description="Breaking-news alerts (alert only, never posts).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="start all watchers and alerting").set_defaults(func=_cmd_run)

    p = sub.add_parser("check-sources", help="fetch every RSS/YouTube feed once and report status")
    p.add_argument("--name", help="only sources whose name contains this text")
    p.set_defaults(func=_cmd_check_sources)

    p = sub.add_parser("items", help="show recently stored items")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--status", choices=["new", "seeded", "stale"])
    p.set_defaults(func=_cmd_items)

    p = sub.add_parser("test-alert", help="send a test alert to your laptop/phone")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--urgent", action="store_true", help="loud ring until dismissed (default)")
    g.add_argument("--normal", action="store_true", help="single chime")
    p.set_defaults(func=_cmd_test_alert)

    p = sub.add_parser("replay", help="replay recorded items through the pipeline (dry run by default)")
    p.add_argument("fixture")
    p.add_argument("--send", action="store_true", help="really deliver alerts (default: print only)")
    p.add_argument("--no-ai", action="store_true", help="skip Haiku; use raw headlines")
    p.add_argument("--realtime", action="store_true", help="honour each event's at_s delay")
    p.set_defaults(func=_cmd_replay)

    p = sub.add_parser("mute", help="silence rings for a while, e.g. `mute 30m`")
    p.add_argument("duration", type=parse_duration)
    p.set_defaults(func=_cmd_mute)
    sub.add_parser("unmute", help="end mute now").set_defaults(func=_cmd_unmute)

    p = sub.add_parser("stats", help="latency per source, alerts sent, AI cost")
    p.add_argument("--hours", type=float, default=24)
    p.set_defaults(func=_cmd_stats)

    p = sub.add_parser("healthcheck", help="exit 0 if the running process is alive")
    p.add_argument("--max-age", type=float, default=180, help="max heartbeat age in seconds")
    p.set_defaults(func=_cmd_healthcheck)
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
