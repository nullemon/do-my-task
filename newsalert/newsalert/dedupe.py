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


# --------------------------------------------------------------------------- story clustering
#
# Items about the same event (same subject + same event type within the cluster
# window) join one story. Cheap signals first: shared watchlist entities, an
# event-type keyword guess, and headline token overlap. Only ambiguous cases
# (same entity, unclear event) are sent to Haiku as a tie-break.

import re as _re
from dataclasses import dataclass as _dataclass, field as _field

from .watchlist import WatchlistIndex as _WatchlistIndex, has_cjk as _has_cjk

# Order matters: the first matching type wins ("died after arrest" -> death).
_EVENT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("death", ["died", "dies", "dead at", "death of", "deaths in ", "passed away", "passes away", "obituary",
               "killed", "rip ", "死去", "逝去", "死亡", "亡くな", "訃報", "永眠"]),
    ("arrest", ["arrested", "arrest", "charged with", "indicted", "逮捕", "書類送検"]),
    ("health", ["hospitalized", "hospitalised", "diagnosed", "surgery", "health reasons",
                "medical leave", "入院", "療養", "体調不良", "休養", "手術"]),
    ("cancellation", ["cancelled", "canceled", "cancels", "axed", "scrapped", "中止", "打ち切り"]),
    ("delay", ["delayed", "postponed", "pushed back", "delay", "延期"]),
    ("casting", ["cast as", "joins cast", "joins the cast", "casting", "to star in", "to play",
                 "voice cast", "キャスト", "出演決定", "声優"]),
    ("award", ["wins", "won", "award", "awards", "nominated", "nominations", "受賞", "大賞", "ノミネート"]),
    ("controversy", ["controversy", "backlash", "apologizes", "apologises", "scandal", "lawsuit",
                     "sued", "炎上", "謝罪", "不倫", "騒動"]),
    ("announcement", ["announces", "announced", "announcement", "season", "sequel", "adaptation",
                      "renewed", "trailer", "teaser", "release date", "premiere", "green-lit",
                      "greenlit", "発表", "決定", "アニメ化", "制作決定", "放送開始", "新作"]),
]
EVENT_TYPES = ["death", "announcement", "delay", "cancellation", "casting", "award", "arrest",
               "health", "controversy", "other"]

_STOPWORDS = set(
    "a an the of in on at to for from by with and or but is are was were be been as it its this that "
    "these those has have had will would can could new news says said after before over into about "
    "his her their they he she you we our up out more than just first last".split()
)
_WORD = _re.compile(r"\w+")


def event_hint(text: str) -> str | None:
    """Keyword guess at the event type, or None if nothing obvious."""
    t = " " + text.casefold() + " "
    for event, words in _EVENT_KEYWORDS:
        if any(w in t for w in words):
            return event
    return None


def title_tokens(text: str) -> set[str]:
    """Content tokens; CJK runs become character bigrams so Japanese titles compare too."""
    norm = normalize_text(text)
    out: set[str] = set()
    for word in _WORD.findall(norm):
        if _has_cjk(word):
            out.update(word[i : i + 2] for i in range(max(len(word) - 1, 1)))
        elif word not in _STOPWORDS and (len(word) > 2 or word.isdigit()):
            out.add(word)
    return out


def token_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b)) if min(len(a), len(b)) >= 3 else len(a & b) / max(len(a), len(b))


@_dataclass
class ItemFeatures:
    entities: set[str]          # watchlist entry names mentioned
    risky_only: bool            # every entity hit is a match_risk entry (e.g. "Friends")
    event: str | None
    tokens: set[str]            # headline tokens minus the matched watchlist names


@_dataclass
class StoryFeatures:
    story_id: int
    subject_key: str
    event_type: str | None
    entities: set[str] = _field(default_factory=set)
    tokens: list[set[str]] = _field(default_factory=list)


@_dataclass
class ClusterDecision:
    story_id: int | None        # join this story
    ambiguous: list[int]        # candidates worth an AI tie-break
    reason: str


def item_features(title: str, text: str, index: _WatchlistIndex) -> ItemFeatures:
    matches = index.find(f"{title}\n{text}")
    entities = {m.entry.name for m in matches}
    risky_only = bool(matches) and all(m.entry.match_risk for m in matches)
    # Names alone must not make two headlines look alike ("X wins award" vs "X arrested"),
    # so the overlap score only counts the other words.
    name_tokens: set[str] = set()
    for m in matches:
        if not m.entry.match_risk:
            name_tokens |= title_tokens(m.alias) | title_tokens(m.entry.name)
    tokens = title_tokens(title) - name_tokens
    return ItemFeatures(entities, risky_only, event_hint(f"{title} {text[:300]}"), tokens)


def match_story(
    item: ItemFeatures,
    stories: list[StoryFeatures],
    *,
    title_similarity: float,
    subject_in_text: callable = None,
) -> ClusterDecision:
    """Pick the existing story this item belongs to, if the cheap signals are clear."""
    best: tuple[float, int, str] | None = None
    ambiguous: list[int] = []
    for s in stories:
        sim = max((token_similarity(item.tokens, t) for t in s.tokens), default=0.0)
        shared = bool(item.entities & s.entities) and not item.risky_only
        if not shared and subject_in_text is not None and s.subject_key:
            shared = subject_in_text(s.subject_key)
        same_event = item.event is not None and item.event == s.event_type
        diff_event = item.event is not None and s.event_type not in (None, "other") and item.event != s.event_type

        if sim >= title_similarity and not diff_event:
            score, why = 2.0 + sim, f"headline overlap {sim:.2f}"
        elif shared and same_event:
            score, why = 1.5 + sim, f"same entity + same event ({s.event_type})"
        elif shared and not diff_event and sim >= 0.25:
            score, why = 1.0 + sim, f"same entity + overlap {sim:.2f}"
        else:
            if shared and not diff_event:
                ambiguous.append(s.story_id)
            continue
        if best is None or score > best[0]:
            best = (score, s.story_id, why)
    if best is not None:
        return ClusterDecision(best[1], [], best[2])
    return ClusterDecision(None, ambiguous, "no clear match" if not ambiguous else "same entity, unclear event")
