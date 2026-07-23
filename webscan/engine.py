"""Core scanning engine.

Design goals:
  * Zero third-party dependencies (stdlib urllib only).
  * Fast: concurrent workers via ThreadPoolExecutor, results streamed as they
    complete.
  * Accurate: a soft-404 baseline is measured first so bogus "200 OK" pages
    (SPA catch-alls, custom error pages) don't drown real findings.
  * Full request control: override Host, inject IP-spoofing headers, custom
    User-Agent / headers — for testing your OWN server / IP-based controls.

Nothing here is destructive: every request is a GET/HEAD. This is a read-only
exposure scanner for sites you own or are authorized to test.
"""

from __future__ import annotations

import gzip
import io
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from . import wordlists

# Headers used when the user asks to "spoof" an IP. These are the headers a
# reverse proxy / app commonly trusts for the client's real address; setting
# them lets you test whether IP allow-lists on your own server can be bypassed.
IP_SPOOF_HEADERS = [
    "X-Forwarded-For",
    "X-Real-IP",
    "X-Originating-IP",
    "X-Remote-IP",
    "X-Remote-Addr",
    "X-Client-IP",
    "Client-IP",
    "True-Client-IP",
    "X-Forwarded-Host",
]

DEFAULT_UA = "webscan/1.0 (+authorized-security-scan)"

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
    "none": 5,
}


@dataclass
class ScanConfig:
    targets: list[str]                      # base URLs, e.g. https://example.com
    base_path: str = "/"                    # path prefix to scan under
    wordlist: str = "common"                # profile name
    custom_paths: list[str] = field(default_factory=list)
    concurrency: int = 20
    timeout: float = 8.0
    method: str = "GET"                     # GET or HEAD
    follow_redirects: bool = False
    verify_tls: bool = True
    delay: float = 0.0                      # per-request politeness delay (s)
    user_agent: str = DEFAULT_UA
    # --- spoofing / own-server testing ---
    host_header: str = ""                   # override Host (hit origin IP as domain)
    spoof_ip: str = ""                      # inject IP_SPOOF_HEADERS with this value
    extra_headers: dict[str, str] = field(default_factory=dict)

    def build_jobs(self):
        """Expand config into a flat list of (target, entry) jobs."""
        entries = list(wordlists.profile(self.wordlist))
        seen = {e["path"] for e in entries}
        for p in self.custom_paths:
            p = p.strip()
            if p and p not in seen:
                seen.add(p)
                entries.append(
                    {"path": p, "category": "custom", "severity": "info",
                     "description": "User-supplied path"}
                )
        jobs = []
        for target in self.targets:
            target = target.strip()
            if not target:
                continue
            for entry in entries:
                jobs.append((target, entry))
        return jobs


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize_target(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    parts = urlsplit(url)
    # Drop any path/query on the base target; scanning adds its own.
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def join_url(target: str, base_path: str, rel: str) -> str:
    parts = urlsplit(target)
    bp = "/" + base_path.strip("/") if base_path.strip("/") else ""
    full_path = (bp + "/" + rel.lstrip("/")).replace("//", "/")
    if not full_path.startswith("/"):
        full_path = "/" + full_path
    # Preserve a trailing slash (directory candidates rely on it).
    if rel.endswith("/") and not full_path.endswith("/"):
        full_path += "/"
    return urlunsplit((parts.scheme, parts.netloc, full_path, "", ""))


# ---------------------------------------------------------------------------
# Low-level fetch
# ---------------------------------------------------------------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # suppress auto-follow; we record the redirect instead


def _make_opener(config: ScanConfig):
    handlers = []
    if config.verify_tls:
        ctx = ssl.create_default_context()
    else:
        ctx = ssl._create_unverified_context()
    handlers.append(urllib.request.HTTPSHandler(context=ctx))
    if not config.follow_redirects:
        handlers.append(_NoRedirect())
    return urllib.request.build_opener(*handlers)


def _headers_for(config: ScanConfig) -> dict:
    headers = {
        "User-Agent": config.user_agent or DEFAULT_UA,
        "Accept": "*/*",
        "Accept-Encoding": "gzip",
        "Connection": "close",
    }
    if config.host_header:
        headers["Host"] = config.host_header
    if config.spoof_ip:
        for h in IP_SPOOF_HEADERS:
            headers[h] = config.spoof_ip
    for k, v in (config.extra_headers or {}).items():
        if k:
            headers[k] = v
    return headers


def _read_body(resp, limit: int = 4096) -> bytes:
    raw = resp.read(limit + 1)
    if resp.headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError:
            pass
    return raw[:limit]


def fetch(url: str, config: ScanConfig, opener, body_limit: int = 4096) -> dict:
    """Perform one request. Returns a raw response dict (never raises).

    body_limit caps how many bytes of the response body are read — small for
    scanning, large for the response viewer.
    """
    headers = _headers_for(config)
    req = urllib.request.Request(url, headers=headers, method=config.method)
    started = time.monotonic()
    try:
        with opener.open(req, timeout=config.timeout) as resp:
            body = b"" if config.method == "HEAD" else _read_body(resp, body_limit)
            return {
                "status": resp.status,
                "location": resp.headers.get("Location", ""),
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": resp.headers.get("Content-Length", ""),
                "server": resp.headers.get("Server", ""),
                "body": body,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "error": "",
            }
    except urllib.error.HTTPError as e:
        # 4xx/5xx come back here — still meaningful (403/401/500 etc.)
        try:
            body = b"" if config.method == "HEAD" else e.read()[:4096]
        except Exception:
            body = b""
        return {
            "status": e.code,
            "location": e.headers.get("Location", "") if e.headers else "",
            "content_type": e.headers.get("Content-Type", "") if e.headers else "",
            "content_length": e.headers.get("Content-Length", "") if e.headers else "",
            "server": e.headers.get("Server", "") if e.headers else "",
            "body": body,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "error": "",
        }
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as e:
        return {
            "status": 0, "location": "", "content_type": "", "content_length": "",
            "server": "", "body": b"",
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "error": str(getattr(e, "reason", e)),
        }


# ---------------------------------------------------------------------------
# Soft-404 baseline
# ---------------------------------------------------------------------------

def measure_baseline(target: str, config: ScanConfig, opener) -> dict:
    """Request two paths that almost certainly do not exist, so we can tell a
    real 200 from a catch-all that returns 200 for everything. We keep the body
    to compare *content* (not just length) against real responses later."""
    body = b""
    status = 0
    for probe_name in ("webscan-baseline-e3f8a1c7-doesnotexist",
                       "webscan-baseline-9b2d/another-missing.zzz"):
        r = fetch(join_url(target, config.base_path, probe_name), config, opener)
        status = r["status"]
        body = r["body"]
        if status != 200:
            break  # a proper 404/whatever — no catch-all, easy case
    return {"status": status, "length": len(body),
            "body": _text(body)[:2048]}


def _looks_like_soft404(resp: dict, baseline: dict) -> bool:
    """True if a 200 response is probably the site's catch-all, not a real hit.

    Compares *content similarity* to the baseline (a site that 200s for every
    path returns the same/similar page). Length alone is unreliable — a small
    real file can match the length of the catch-all — so content wins.
    """
    if resp["status"] != 200 or baseline.get("status") != 200:
        return False
    bbody = baseline.get("body", "")
    if not bbody:
        # No baseline body to compare; fall back to a loose length match.
        blen = baseline.get("length", -1)
        return blen > 0 and abs(len(resp["body"]) - blen) <= max(16, blen * 0.02)
    ratio = _quick_ratio(_text(resp["body"])[:2048], bbody)
    return ratio >= 0.90


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _text(body: bytes) -> str:
    return body.decode("utf-8", "replace")


def _quick_ratio(a: str, b: str) -> float:
    """Cheap content-similarity ratio in [0,1] without importing difflib on the
    hot path for every call (difflib is fine here — small, truncated strings)."""
    import difflib
    return difflib.SequenceMatcher(None, a, b).quick_ratio()


def _signature_match(path: str, body_text: str):
    """Return (note) if a known content signature for `path` matches, else None."""
    low = body_text.lower()
    for key, (needle, note) in wordlists.CONTENT_SIGNATURES.items():
        if key in path and needle.lower() in low:
            return note
    return None


def classify(entry: dict, resp: dict, baseline: dict) -> dict:
    """Turn a raw response into a finding with a verdict + adjusted severity."""
    status = resp["status"]
    path = entry["path"]
    body_text = _text(resp["body"])
    base_sev = entry["severity"]

    finding = {
        "verdict": "not-found",     # exposed | protected | exists | redirect | error | not-found
        "severity": "none",
        "confirmed": False,
        "notes": [],
    }

    if status == 0:
        finding.update(verdict="error", severity="none",
                       notes=[resp.get("error") or "request failed"])
        return finding

    # Directory listing enabled — this is always noteworthy.
    if status == 200 and any(sig.lower() in body_text.lower()
                             for sig in wordlists.DIRECTORY_LISTING_SIGNATURES):
        finding.update(
            verdict="exposed", confirmed=True,
            severity=_max_sev(base_sev, "high"),
            notes=["Directory listing is ENABLED — contents are browsable"],
        )
        return finding

    if status == 200:
        # A matching content signature is decisive proof the file is real and
        # served — it overrides soft-404 suppression (a real .env can happen to
        # be the same size as the site's catch-all page).
        sig = _signature_match(path, body_text)
        if sig:
            finding.update(verdict="exposed", confirmed=True, severity=base_sev,
                           notes=[f"Confirmed: {sig}"])
            return finding
        if _looks_like_soft404(resp, baseline):
            finding.update(verdict="not-found", severity="none",
                           notes=["200 but matches site catch-all (likely soft-404)"])
            return finding
        finding.update(verdict="exposed", severity=base_sev,
                       notes=["Reachable (HTTP 200)"])
        return finding

    if status in (301, 302, 303, 307, 308):
        loc = resp["location"]
        low = loc.lower()
        if any(w in low for w in ("login", "signin", "auth", "sso")):
            finding.update(verdict="protected", severity="info",
                           notes=[f"Redirects to auth ({loc})"])
        else:
            finding.update(verdict="redirect", severity="info",
                           notes=[f"Redirects to {loc or '(unknown)'}"])
        return finding

    if status == 401:
        finding.update(verdict="protected", severity="info",
                       notes=["Requires authentication (401) — good"])
        return finding

    if status == 403:
        # Path exists but is forbidden. Worth reporting: attacker knows it's there,
        # and it may be bypassable via the spoof headers.
        finding.update(verdict="exists", severity=_min_sev(base_sev, "low"),
                       notes=["Exists but forbidden (403) — confirms presence"])
        return finding

    if status in (405, 501):
        finding.update(verdict="exists", severity="info",
                       notes=[f"Exists (HTTP {status})"])
        return finding

    if 500 <= status < 600:
        finding.update(verdict="exists", severity="low",
                       notes=[f"Server error (HTTP {status}) — may leak stack trace"])
        return finding

    return finding


def _max_sev(a: str, b: str) -> str:
    return a if SEVERITY_ORDER.get(a, 9) <= SEVERITY_ORDER.get(b, 9) else b


def _min_sev(a: str, b: str) -> str:
    return a if SEVERITY_ORDER.get(a, 9) >= SEVERITY_ORDER.get(b, 9) else b


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def scan(config: ScanConfig):
    """Run a scan, yielding event dicts as work progresses.

    Event types:
      {"type": "start",   "total": N, "targets": [...]}
      {"type": "baseline","target": t, "status": s}
      {"type": "result",  ...finding...}
      {"type": "progress","done": d, "total": N}
      {"type": "done",    "summary": {...}}
    """
    config.targets = [normalize_target(t) for t in config.targets if t.strip()]
    jobs = config.build_jobs()
    total = len(jobs)

    yield {"type": "start", "total": total, "targets": config.targets}

    opener = _make_opener(config)

    # Baseline per target (soft-404 detection).
    baselines = {}
    for target in config.targets:
        b = measure_baseline(target, config, opener)
        baselines[target] = b
        yield {"type": "baseline", "target": target,
               "status": b["status"], "body_length": b["length"]}

    done = 0
    summary = {"exposed": 0, "protected": 0, "exists": 0,
               "redirect": 0, "error": 0, "by_severity": {}}

    def work(target, entry):
        url = join_url(target, config.base_path, entry["path"])
        if config.delay:
            time.sleep(config.delay)
        resp = fetch(url, config, opener)
        finding = classify(entry, resp, baselines.get(target, {}))
        return {
            "type": "result",
            "target": target,
            "url": url,
            "path": entry["path"],
            "category": entry["category"],
            "description": entry["description"],
            "status": resp["status"],
            "content_type": resp["content_type"],
            "content_length": resp["content_length"] or len(resp["body"]),
            "server": resp["server"],
            "elapsed_ms": resp["elapsed_ms"],
            "location": resp["location"],
            "verdict": finding["verdict"],
            "severity": finding["severity"],
            "confirmed": finding["confirmed"],
            "notes": finding["notes"],
        }

    workers = max(1, min(config.concurrency, 64))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, t, e) for (t, e) in jobs]
        for fut in as_completed(futures):
            res = fut.result()
            done += 1
            v = res["verdict"]
            if v in summary:
                summary[v] += 1
            if res["severity"] not in ("none",):
                summary["by_severity"][res["severity"]] = \
                    summary["by_severity"].get(res["severity"], 0) + 1
            # Only stream interesting results (skip clean not-found noise),
            # but always emit progress.
            if v != "not-found":
                yield res
            yield {"type": "progress", "done": done, "total": total}

    yield {"type": "done", "summary": summary}


def scan_collect(config: ScanConfig) -> dict:
    """Convenience: run a scan and return findings + summary (no streaming)."""
    findings = []
    summary = {}
    for ev in scan(config):
        if ev["type"] == "result":
            findings.append(ev)
        elif ev["type"] == "done":
            summary = ev["summary"]
    findings.sort(key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), r["url"]))
    return {"findings": findings, "summary": summary}
