"""Command-line interface for webscan.

Examples
--------
  # Scan one site with the default 'common' wordlist:
  python3 -m webscan.cli https://example.com

  # Scan a sub-path with more workers and export JSON:
  python3 -m webscan.cli https://example.com --path /app --workers 40 --json out.json

  # Bulk scan several targets from a file:
  python3 -m webscan.cli --targets-file sites.txt --wordlist sensitive

  # Test your own origin server IP while presenting your domain, and spoof a
  # trusted client IP to check IP-based access controls:
  python3 -m webscan.cli http://203.0.113.10 --host-header example.com \
      --spoof-ip 127.0.0.1
"""

from __future__ import annotations

import argparse
import json
import sys

from . import wordlists
from .engine import ScanConfig, SEVERITY_ORDER, scan

# ANSI colors (auto-disabled when not a TTY).
_COLORS = {
    "critical": "\033[95m", "high": "\033[91m", "medium": "\033[93m",
    "low": "\033[96m", "info": "\033[90m", "none": "",
    "reset": "\033[0m", "bold": "\033[1m",
}


def _c(text, key, enable):
    if not enable:
        return text
    return f"{_COLORS.get(key, '')}{text}{_COLORS['reset']}"


def build_parser():
    p = argparse.ArgumentParser(
        prog="webscan",
        description="Read-only exposure scanner for sites you own/are authorized to test.",
    )
    p.add_argument("targets", nargs="*", help="Base URL(s), e.g. https://example.com")
    p.add_argument("--targets-file", help="File with one target URL per line")
    p.add_argument("--path", default="/", help="Base path to scan under (default /)")
    p.add_argument("--wordlist", default="common",
                   choices=wordlists.profile_names(),
                   help="Wordlist profile (default common)")
    p.add_argument("--paths-file", help="Extra custom paths, one per line")
    p.add_argument("--workers", type=int, default=20, help="Concurrent requests")
    p.add_argument("--timeout", type=float, default=8.0, help="Per-request timeout (s)")
    p.add_argument("--method", default="GET", choices=["GET", "HEAD"])
    p.add_argument("--follow-redirects", action="store_true")
    p.add_argument("--insecure", action="store_true", help="Skip TLS verification")
    p.add_argument("--delay", type=float, default=0.0, help="Politeness delay per request")
    p.add_argument("--user-agent", default=None)
    p.add_argument("--host-header", default="", help="Override Host header")
    p.add_argument("--spoof-ip", default="",
                   help="Inject X-Forwarded-For / X-Real-IP etc. with this value")
    p.add_argument("--header", action="append", default=[],
                   metavar="K:V", help="Extra header (repeatable)")
    p.add_argument("--json", metavar="FILE", help="Write full results as JSON")
    p.add_argument("--no-color", action="store_true")
    return p


def _load_lines(path):
    with open(path, "r", encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def main(argv=None):
    args = build_parser().parse_args(argv)

    targets = list(args.targets)
    if args.targets_file:
        targets += _load_lines(args.targets_file)
    if not targets:
        build_parser().error("no targets given (positional URL or --targets-file)")

    custom_paths = _load_lines(args.paths_file) if args.paths_file else []

    extra_headers = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            extra_headers[k.strip()] = v.strip()

    from .engine import DEFAULT_UA
    config = ScanConfig(
        targets=targets,
        base_path=args.path,
        wordlist=args.wordlist,
        custom_paths=custom_paths,
        concurrency=args.workers,
        timeout=args.timeout,
        method=args.method,
        follow_redirects=args.follow_redirects,
        verify_tls=not args.insecure,
        delay=args.delay,
        user_agent=args.user_agent or DEFAULT_UA,
        host_header=args.host_header,
        spoof_ip=args.spoof_ip,
        extra_headers=extra_headers,
    )

    color = sys.stdout.isatty() and not args.no_color
    print(_c("webscan — authorized-use exposure scan", "bold", color))
    if config.spoof_ip or config.host_header:
        print(_c(f"  spoof: Host={config.host_header or '-'} IP={config.spoof_ip or '-'}",
                 "info", color))

    findings = []
    summary = {}
    total = 0
    for ev in scan(config):
        t = ev["type"]
        if t == "start":
            total = ev["total"]
            print(_c(f"  {total} checks across {len(ev['targets'])} target(s)\n",
                     "info", color))
        elif t == "baseline":
            print(_c(f"  baseline {ev['target']}: HTTP {ev['status']} "
                     f"({ev['body_length']}B)", "info", color))
        elif t == "result":
            findings.append(ev)
            sev = ev["severity"]
            tag = f"[{sev.upper()}]" if sev != "none" else f"[{ev['verdict']}]"
            mark = "✓" if ev["confirmed"] else " "
            line = (f"  {mark} {_c(tag.ljust(11), sev, color)} "
                    f"{ev['status']:>3}  {ev['url']}")
            print(line)
            for note in ev["notes"]:
                print(_c(f"        └ {note}", "info", color))
        elif t == "done":
            summary = ev["summary"]

    findings.sort(key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), r["url"]))
    print()
    print(_c("Summary", "bold", color))
    print(f"  exposed={summary.get('exposed',0)} "
          f"exists={summary.get('exists',0)} "
          f"protected={summary.get('protected',0)} "
          f"redirect={summary.get('redirect',0)} "
          f"error={summary.get('error',0)}")
    by_sev = summary.get("by_severity", {})
    if by_sev:
        parts = [f"{_c(k, k, color)}={v}"
                 for k, v in sorted(by_sev.items(),
                                    key=lambda kv: SEVERITY_ORDER.get(kv[0], 9))]
        print("  severity: " + "  ".join(parts))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"findings": findings, "summary": summary}, fh, indent=2)
        print(f"\n  wrote {args.json}")

    # Exit non-zero if anything exposed/confirmed — handy for CI.
    exposed = [f for f in findings if f["verdict"] == "exposed"]
    return 2 if exposed else 0


if __name__ == "__main__":
    sys.exit(main())
