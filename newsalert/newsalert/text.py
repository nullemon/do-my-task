"""Small text helpers shared by watchers, dedupe and formatting."""

from __future__ import annotations

import html
import re
import unicodedata

_SCRIPT_STYLE = re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_URL = re.compile(r"https?://\S+")
_NON_WORD = re.compile(r"[^\w\s]")


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    value = _SCRIPT_STYLE.sub(" ", value)
    value = _TAG.sub(" ", value)
    value = html.unescape(value)
    return _WS.sub(" ", value).strip()


def truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def normalize_text(value: str) -> str:
    """Case/width/punctuation-insensitive form used for exact-duplicate hashing.

    `\\w` is Unicode-aware, so Japanese text is kept intact.
    """
    v = unicodedata.normalize("NFKC", value).casefold()
    v = _URL.sub(" ", v)
    v = _NON_WORD.sub(" ", v)
    return _WS.sub(" ", v).strip()


def humanize_age(seconds: float | None) -> str:
    if seconds is None:
        return "no date"
    if seconds < 0:
        return "just now"
    if seconds < 90:
        return f"{int(seconds)}s ago"
    if seconds < 90 * 60:
        return f"{int(seconds // 60)}m ago"
    if seconds < 36 * 3600:
        return f"{seconds / 3600:.1f}h ago"
    return f"{seconds / 86400:.1f}d ago"
