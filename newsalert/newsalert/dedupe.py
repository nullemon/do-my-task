"""Exact dedupe (URL / text hash / feed id) and the stale-backlog rule.

Story clustering (same subject + event within 6h) is added in build step 4.
"""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .text import normalize_text

# Query parameters that only track the click and never change the content.
_TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref_src",
    "ref_url", "cmpid", "ncid", "ocid", "smid", "si", "feature", "rss", "ito",
    "at_medium", "at_campaign", "taid", "ved", "oc",
}
_HOST_PREFIXES = ("www.", "m.", "mobile.")
_HOST_ALIASES = {"twitter.com": "x.com"}
# Very short texts ("New trailer!") are too generic to hash-dedupe. Measured in UTF-8
# bytes so dense Japanese headlines (3 bytes/char) still qualify.
_MIN_HASH_BYTES = 24


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if not parts.netloc:
        return url
    host = (parts.hostname or "").lower()
    for prefix in _HOST_PREFIXES:
        if host.startswith(prefix):
            host = host[len(prefix):]
            break
    host = _HOST_ALIASES.get(host, host)
    port = parts.port
    if port and port not in (80, 443):
        host = f"{host}:{port}"
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    query.sort()
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit(("https", host, path, urlencode(query), ""))


def text_hash(text: str) -> str:
    """Stable hash of the normalized text. Empty-ish texts hash to '' (never matched)."""
    norm = normalize_text(text)
    raw = norm.encode("utf-8")
    if len(raw) < _MIN_HASH_BYTES:
        return ""
    return hashlib.sha256(raw).hexdigest()[:32]


def is_stale(published_at: float | None, fetched_at: float, stale_minutes: int) -> bool:
    """True if the item was published more than `stale_minutes` before we fetched it.

    Items with no date, or dated in the future (bad feed clocks), count as fresh.
    """
    if published_at is None:
        return False
    return (fetched_at - published_at) > stale_minutes * 60
