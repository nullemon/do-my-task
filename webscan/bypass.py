"""403 / Forbidden bypass tester.

You locked a directory (e.g. with .htaccess) and it returns "403 Forbidden" —
but somehow people still reach it. This module probes *how*: it takes the
locked URL, confirms it's actually forbidden, then throws a matrix of known
access-control bypass techniques at it and reports which ones get through.

Every technique here is a single ordinary HTTP request with a mutated path,
method, or header — the meaningful, browser-possible sense of "spoofing" for
testing your OWN server. Nothing forges network packets; nothing is destructive.

Categories:
  * path/encoding    — path normalisation tricks that dodge location rules
  * http-method      — method changes that dodge <Limit GET POST> style rules
  * ip-header        — X-Forwarded-For / X-Real-IP … to dodge IP allow-lists
  * rewrite-header   — X-Original-URL / X-Rewrite-URL / Referer routing tricks
  * infra            — origin-vs-CDN, HTTP version

The engine is deterministic (no AI). webscan/ai.py optionally explains the
results and writes the fix; this module is what proves the hole exists.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from . import engine, wordlists  # reuse fetch(), opener, header building, signatures


@dataclass
class BypassConfig:
    target_url: str                       # the locked URL, e.g. https://site.com/private/
    spoof_ip: str = "127.0.0.1"           # IP to try in IP-trust headers
    host_header: str = ""                 # optional Host override (origin testing)
    extra_headers: dict = field(default_factory=dict)
    concurrency: int = 20
    timeout: float = 8.0
    verify_tls: bool = True
    user_agent: str = engine.DEFAULT_UA


# Statuses that mean "locked / access denied" — the expected baseline.
FORBIDDEN = {401, 403, 407}
# Statuses that mean "content was served" — a bypass when baseline was forbidden.
SERVED = {200, 201, 202, 203, 206}


# ---------------------------------------------------------------------------
# Technique generation
# ---------------------------------------------------------------------------

def _split(url):
    p = urlsplit(url)
    return p.scheme, p.netloc, p.path or "/", p.query


def _url(scheme, netloc, path, query=""):
    return urlunsplit((scheme, netloc, path, query, ""))


def path_mutations(path: str):
    """Yield (mutated_path, technique, description, fix) path variants.

    These target servers that apply the .htaccess/location rule to the literal
    request path but resolve a *different* path on disk — so a rule on
    `/private/` never fires for `/PRIVATE/`, `/private/.`, `/private%2f`, etc.
    """
    p = path
    base = p.rstrip("/")
    is_dir = p.endswith("/")
    seg = base.rsplit("/", 1)[-1]           # last path segment
    parent = base[: len(base) - len(seg)]   # everything up to it (keeps slash)

    out = []

    def add(mp, tech, desc, fix):
        out.append((mp, tech, desc, fix))

    # Trailing-character tricks
    add(base + "/.", "path: trailing /.",
        "Appended /. — Apache may normalise it after the rule matched",
        "Match the path with and without a trailing dot; enable `AllowOverride` "
        "rewrite normalisation or block `/.` in your rule.")
    add(base + "/./", "path: /./ segment",
        "Inserted /./ current-dir segment",
        "Normalise `/./` before applying access rules (mod_rewrite `RewriteRule ^ - [L]` after canonicalising).")
    add(base + "//", "path: double slash",
        "Doubled trailing slash",
        "Collapse repeated slashes (`MergeSlashes On` on Apache 2.4.39+) before matching.")
    add("/" + base.lstrip("/") + "..;/", "path: ..;/ (Tomcat)",
        "Appended ..;/ path-parameter (Tomcat/Java bypass)",
        "Upgrade the app server; reject `;` path parameters at the proxy.")
    add(base + ";/", "path: ;/ parameter",
        "Appended ;/ empty path parameter",
        "Strip path parameters (everything after `;`) before matching rules.")
    add(base + "%20", "path: trailing %20",
        "Appended URL-encoded space",
        "Decode and trim trailing whitespace before matching; block `%20` on protected paths.")
    add(base + "%09", "path: trailing %09 (tab)",
        "Appended URL-encoded tab",
        "Decode control whitespace before matching.")
    add(base + "%00", "path: trailing %00 (null)",
        "Appended URL-encoded null byte",
        "Reject `%00` outright — it should never appear in a legitimate path.")

    # Encoded path separators — the flagship 403 dodge. The rule matches the
    # literal (encoded) path; the server decodes it afterwards and serves the file.
    add(base + "%2f", "path: %2f (encoded slash)",
        "Appended a URL-encoded slash",
        "URL-decode the request path BEFORE evaluating access rules "
        "(`AllowEncodedSlashes NoDecode` alone isn't enough — normalise first).")
    add(base + "/%2e", "path: %2e (encoded dot)",
        "Appended an encoded dot segment (/%2e)",
        "Decode and canonicalise `%2e`/`%2f` before matching; on nginx use a normalised "
        "`location` rather than a raw prefix match.")
    # Double URL-encoding — dodges proxies/WAFs that decode exactly once, then
    # pass `%2f`/`%2e` to an origin that decodes again.
    add(base + "%252f", "path: %252f (double-encoded slash)",
        "Appended a double URL-encoded slash (%25 2f)",
        "Reject or fully-normalise multiply-encoded paths at the edge — decode until stable, "
        "then match. A single-decode WAF in front of a decoding origin is the classic hole.")
    add(base + "/%252e", "path: %252e (double-encoded dot)",
        "Appended a double URL-encoded dot",
        "Same as above — normalise repeated percent-encoding before applying rules.")
    add(base + "?", "path: trailing ?",
        "Appended empty query separator",
        "Ensure the rule matches on the path only, independent of a trailing `?`.")
    add(base + "#", "path: trailing #",
        "Appended fragment separator",
        "Fragments should be stripped server-side; verify your rule isn't fooled by a literal `#`.")

    # Suffix tricks (files served as source / alternate handlers)
    for suffix, name in ((".json", ".json"), (".html", ".html"),
                         ("~", "~ backup"), (".", "trailing dot")):
        add(base + suffix, f"path: {name} suffix",
            f"Appended {suffix!r} suffix",
            f"Deny access to the resource by content, not just by exact name — a rule on "
            f"`{seg}` won't cover `{seg}{suffix}`.")

    # Case variations (case-insensitive filesystems: macOS, Windows, some mounts)
    if seg and seg.lower() != seg.upper():
        for variant, name in ((seg.upper(), "UPPER"),
                              (seg.capitalize(), "Capitalised"),
                              (seg.swapcase(), "sWAPPED")):
            if variant != seg:
                mp = parent + variant + ("/" if is_dir else "")
                add(mp, f"path: {name} case",
                    f"Changed case of the last segment to {variant!r}",
                    "Make your rule case-insensitive (`<Directory ~ \"(?i)/private\">`), or move the "
                    "resource off a case-insensitive filesystem.")

    # Encoding of the first character of the last segment
    if seg:
        enc = "%%%02x" % ord(seg[0])
        mp = parent + enc + seg[1:] + ("/" if is_dir else "")
        add(mp, "path: %-encoded char",
            f"URL-encoded first char ({seg[0]!r} -> {enc})",
            "Decode percent-encoding before matching (URL-normalise in the proxy/WAF).")

    # Leading tricks
    add("/./" + base.lstrip("/") + ("/" if is_dir else ""), "path: /./ prefix",
        "Prefixed /./",
        "Canonicalise leading `/./` before matching.")
    add("//" + base.lstrip("/") + ("/" if is_dir else ""), "path: // prefix",
        "Prefixed //",
        "Collapse leading double slashes (`MergeSlashes On`).")

    # Toggle trailing slash
    add(base if is_dir else base + "/", "path: slash toggle",
        "Toggled the trailing slash",
        "Apply the rule to both `/private` and `/private/` (a `<Directory>` block covers both; a "
        "`<Location>` regex may not).")

    return out


def header_and_method_attempts(scheme, netloc, path, config: BypassConfig):
    """Yield (method, path, extra_headers, technique, description, fix)."""
    out = []
    full = _url(scheme, netloc, path)
    ip = config.spoof_ip or "127.0.0.1"

    def add(method, mp, headers, tech, desc, fix):
        out.append((method, mp, headers, tech, desc, fix))

    # --- IP-trust headers (Require ip / Deny,Allow bypass) ------------------
    ip_headers_all = {h: ip for h in engine.IP_SPOOF_HEADERS}
    add("GET", path, ip_headers_all, "ip-header: all X-Forwarded-* ",
        f"Sent X-Forwarded-For / X-Real-IP / … = {ip} together",
        "Do NOT trust client IP headers unless the request came from a proxy you control. In Apache, "
        "use `Require ip` against the real connection IP; strip inbound X-Forwarded-* at the edge and "
        "only re-add them on your trusted proxy (mod_remoteip with `RemoteIPTrustedProxy`).")
    for h in ("X-Forwarded-For", "X-Real-IP", "X-Client-IP",
              "True-Client-IP", "X-Originating-IP"):
        add("GET", path, {h: ip}, f"ip-header: {h}",
            f"Sent {h}: {ip}",
            f"Your allow-list is honouring `{h}` from the client. Ignore it unless set by a trusted "
            f"proxy; match on the real remote address instead.")
    # RFC 7239 standard header — different syntax (for=<ip>), often overlooked.
    add("GET", path, {"Forwarded": f"for={ip}"}, "ip-header: Forwarded (RFC 7239)",
        f"Sent Forwarded: for={ip}",
        "The standard `Forwarded` header is honoured by some stacks the same way as X-Forwarded-For. "
        "Strip it at the edge unless it comes from a trusted proxy.")

    # --- Rewrite / routing headers ------------------------------------------
    # X-Original-URL / X-Rewrite-URL: request an ALLOWED path but smuggle the
    # locked path in the header. Servers honouring these route to the locked
    # resource while the .htaccess rule saw the allowed path.
    add("GET", "/", {"X-Original-URL": path}, "rewrite-header: X-Original-URL",
        f"Requested / but set X-Original-URL: {path}",
        "Disable `X-Original-URL`/`X-Rewrite-URL` handling (common on IIS / some PHP setups). Never let "
        "a client header override the routed path that access rules are evaluated against.")
    add("GET", "/", {"X-Rewrite-URL": path}, "rewrite-header: X-Rewrite-URL",
        f"Requested / but set X-Rewrite-URL: {path}",
        "Same as above — reject client-supplied URL-rewrite headers.")

    # Referer-based .htaccess protection (very common for directory/hotlink locks)
    ref = _url(scheme, netloc, path)
    add("GET", path, {"Referer": ref}, "rewrite-header: Referer match",
        f"Sent Referer: {ref}",
        "Referer-based protection is trivially spoofable — never use Referer for access control. Replace "
        "the `RewriteCond %{HTTP_REFERER}` rule with real auth (Basic/Digest, `Require`, or app-level login).")

    # --- HTTP method changes (<Limit GET POST> bypass) ----------------------
    for method in ("POST", "HEAD", "OPTIONS", "PUT", "DELETE", "TRACE", "PATCH"):
        add(method, path, {}, f"http-method: {method}",
            f"Reissued the request as {method}",
            "Your rule limits methods (e.g. `<Limit GET POST>`). Use `<LimitExcept>` instead, which "
            "denies ALL methods except the listed ones — `<Limit>` only covers the methods you name.")
    add("FOO", path, {}, "http-method: arbitrary verb",
        "Used a made-up method (FOO)",
        "An unknown method slipping past confirms a `<Limit>`-style rule. Switch to `<LimitExcept GET POST>`.")
    for ov in ("X-HTTP-Method-Override", "X-HTTP-Method", "X-Method-Override"):
        add("POST", path, {ov: "GET"}, f"http-method: {ov}",
            f"POST + {ov}: GET",
            "Frameworks that honour method-override headers can undo method restrictions. Disable "
            "override headers on protected paths.")

    return out


# Common filenames people reach directly when a directory's *listing* is
# blocked (403) but the files inside are still served. Heavy on images since
# that's the classic "locked img/ folder that's still readable" case.
INSIDE_FILE_NAMES = [
    "index.html", "index.htm", ".htaccess",
    "logo.png", "logo.jpg", "logo.svg", "favicon.ico", "banner.jpg",
    "header.jpg", "bg.jpg", "background.jpg", "hero.jpg", "placeholder.png",
    "avatar.png", "default.jpg", "default.png", "thumb.jpg", "thumbnail.jpg",
    "icon.png", "sprite.png", "image.jpg", "photo.jpg", "img.jpg",
    "1.jpg", "1.png", "0.jpg", "test.jpg", "test.png", "sample.jpg",
    "upload.jpg", "profile.jpg", "cover.jpg",
]

_INSIDE_FIX = (
    "Your lock is on the directory *listing*, not on its contents — hitting the "
    "folder gives 403 (no index / `Options -Indexes`), but every file inside is "
    "still served. People reach the images by their direct URL. To actually block "
    "the contents, deny the files, e.g. in Apache put an .htaccess *inside* the "
    "folder with `Require all denied` (2.4+) or `Order allow,deny` + `Deny from all` "
    "(2.2); or in the vhost:\n"
    "    <Directory \"/var/www/img\">\n"
    "        Require all denied\n"
    "    </Directory>\n"
    "If the images are meant to be public, then the directory 'lock' is cosmetic — "
    "keep listing off but don't expect it to hide the files."
)


def inside_file_probes(path: str):
    """Yield GET attempts for common files inside a locked *directory*.

    Only meaningful when `path` is a directory (ends with '/'): a 200 here means
    the lock only hid the listing while the files stayed public.
    """
    if not path.endswith("/"):
        return []
    out = []
    for name in INSIDE_FILE_NAMES:
        out.append((path + name, f"inside-file: {name}",
                    f"Requested {name} directly inside the locked directory",
                    _INSIDE_FIX))
    return out


def generate_attempts(config: BypassConfig):
    """Build the full attempt list (excluding the baseline)."""
    scheme, netloc, path, _ = _split(config.target_url)
    attempts = []

    # Direct file access inside a locked directory (the "listing is off but the
    # files are public" case) — first, because it's the most common real leak.
    for mp, tech, desc, fix in inside_file_probes(path):
        attempts.append({"method": "GET", "path": mp, "headers": {},
                         "category": "inside-file", "technique": tech,
                         "description": desc, "fix": fix})

    for mp, tech, desc, fix in path_mutations(path):
        attempts.append({"method": "GET", "path": mp, "headers": {},
                         "category": "path", "technique": tech,
                         "description": desc, "fix": fix})

    for method, mp, headers, tech, desc, fix in \
            header_and_method_attempts(scheme, netloc, path, config):
        cat = tech.split(":", 1)[0]
        attempts.append({"method": method, "path": mp, "headers": headers,
                         "category": cat, "technique": tech,
                         "description": desc, "fix": fix})

    return scheme, netloc, attempts


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _base_config(config: BypassConfig) -> engine.ScanConfig:
    """A ScanConfig used only for its fetch settings (opener, headers)."""
    return engine.ScanConfig(
        targets=[], base_path="/", verify_tls=config.verify_tls,
        timeout=config.timeout, user_agent=config.user_agent,
        host_header=config.host_header, spoof_ip="",  # per-attempt headers instead
        extra_headers=config.extra_headers, follow_redirects=False,
    )


def _do_request(scheme, netloc, method, path, extra_headers, base_cfg, opener):
    cfg = engine.ScanConfig(
        targets=[], base_path="/", method=method,
        verify_tls=base_cfg.verify_tls, timeout=base_cfg.timeout,
        user_agent=base_cfg.user_agent, host_header=base_cfg.host_header,
        follow_redirects=False,
        extra_headers={**(base_cfg.extra_headers or {}), **extra_headers},
    )
    url = _url(scheme, netloc, path)
    return url, engine.fetch(url, cfg, opener)


def _similar(a: str, b: str, threshold: float = 0.9) -> bool:
    if not a or not b:
        return False
    return engine._quick_ratio(a[:2048], b[:2048]) >= threshold


def run(config: BypassConfig):
    """Run the bypass test, yielding event dicts.

    Events: start, baseline, result (only bypasses/notable), progress, done.
    """
    scheme, netloc, attempts = generate_attempts(config)
    base_cfg = _base_config(config)
    opener = engine._make_opener(base_cfg)
    orig_path = urlsplit(config.target_url).path or "/"

    # 1) Baseline — confirm the URL is actually locked.
    _, base_resp = _do_request(scheme, netloc, "GET", orig_path, {}, base_cfg, opener)
    baseline_status = base_resp["status"]
    locked = baseline_status in FORBIDDEN
    yield {
        "type": "baseline",
        "url": config.target_url,
        "status": baseline_status,
        "locked": locked,
        "note": (
            "Locked as expected — testing bypasses." if locked else
            (f"Heads up: this URL returned {baseline_status}, not Forbidden. "
             "It may not be locked at all — anything 'reachable' below is just it being open.")
            if baseline_status else
            f"Could not reach the URL ({base_resp.get('error') or 'no response'})."
        ),
    }

    # 2) Controls, so we don't cry "bypass" at a false positive:
    #    - soft404: a nonexistent sibling path. Path-mutation 200s that match
    #      this are the site's catch-all, not the protected resource.
    #    - root: GET "/" (the path the X-Original-URL/X-Rewrite-URL attempts
    #      request). If a rewrite-header 200 just returns "/", the header was
    #      ignored — not a bypass.
    parent = orig_path.rstrip("/").rsplit("/", 1)[0] + "/"
    _, sc = _do_request(scheme, netloc, "GET",
                        parent + "webscan-bypass-40c1f-nope", {}, base_cfg, opener)
    soft404 = engine._text(sc["body"]) if sc["status"] in SERVED else ""
    _, rc = _do_request(scheme, netloc, "GET", "/", {}, base_cfg, opener)
    root_body = engine._text(rc["body"]) if rc["status"] in SERVED else ""

    total = len(attempts)
    yield {"type": "start", "total": total, "baseline_status": baseline_status}

    def work(a):
        url, resp = _do_request(scheme, netloc, a["method"], a["path"],
                                a["headers"], base_cfg, opener)
        status = resp["status"]
        served = status in SERVED
        body_text = engine._text(resp["body"])
        cat = a["category"]

        bypass = served and locked
        verdict_note = ""
        if bypass:
            # Suppress the false positives the controls expose.
            if cat in ("path", "inside-file") and soft404 and _similar(body_text, soft404):
                bypass, verdict_note = False, "matched the site's catch-all page (not a real resource)"
            elif cat == "rewrite-header" and root_body and _similar(body_text, root_body):
                bypass, verdict_note = False, "header ignored — served the normal / page, not the locked resource"

        listing = bypass and any(
            s.lower() in body_text.lower()
            for s in wordlists.DIRECTORY_LISTING_SIGNATURES
        )
        if status in FORBIDDEN:
            verdict = "blocked"
        elif status == 404:
            verdict = "not-found"
        elif 300 <= status < 400:
            verdict = "redirect"
        elif status == 0:
            verdict = "error"
        elif bypass:
            verdict = "BYPASS"
        elif served:
            verdict = "ignored"  # served, but a control proved it isn't the locked resource
        else:
            verdict = "other"

        return {
            "type": "result",
            "technique": a["technique"],
            "category": cat,
            "description": a["description"],
            "fix": a["fix"],
            "method": a["method"],
            "url": url,
            "sent_headers": a["headers"],
            "status": status,
            "content_length": resp["content_length"] or len(resp["body"]),
            "elapsed_ms": resp["elapsed_ms"],
            "bypass": bypass,
            "inside_file": bypass and cat == "inside-file",
            "directory_listing": listing,
            "verdict": verdict,
            "note": verdict_note,
        }

    done = 0
    bypasses = []
    workers = max(1, min(config.concurrency, 64))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, a) for a in attempts]
        for fut in as_completed(futures):
            res = fut.result()
            done += 1
            if res["bypass"]:
                bypasses.append(res)
            # Stream bypasses always; stream a few blocked/other for context.
            if res["bypass"] or res["verdict"] in ("redirect",):
                yield res
            yield {"type": "progress", "done": done, "total": total,
                   "bypasses": len(bypasses)}

    yield {
        "type": "done",
        "baseline_status": baseline_status,
        "locked": locked,
        "bypass_count": len(bypasses),
        "bypasses": bypasses,
    }


def run_collect(config: BypassConfig) -> dict:
    """Run and return a summary dict (no streaming)."""
    baseline = {}
    bypasses = []
    for ev in run(config):
        if ev["type"] == "baseline":
            baseline = ev
        elif ev["type"] == "done":
            bypasses = ev["bypasses"]
    return {"baseline": baseline, "bypasses": bypasses,
            "bypass_count": len(bypasses)}
