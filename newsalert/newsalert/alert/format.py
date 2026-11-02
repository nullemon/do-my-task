"""Turn stories into alerts in the owner's format:

    [ANIME] [OFFICIAL SOURCE] Studio X announces Season 2 of Y
    Summary: one sentence from triage
    Source: @StudioX_official (X) · 47s ago
    Links: original post · other sources so far
"""

from __future__ import annotations

import time
from typing import Iterable, Sequence

from ..confidence import DEATH_WARNING, needs_death_warning
from ..text import humanize_age, truncate
from . import Alert

_TYPE_LABEL = {"rss": "", "youtube": "YouTube", "bluesky": "Bluesky", "x": "X", "wikipedia": "Wikipedia"}


def source_line(item, now: float) -> str:
    """'@StudioX_official (X) · 47s ago' / 'Anime News Network · 2m ago'."""
    kind = _TYPE_LABEL.get(item["source_type"], item["source_type"])
    who = item["source"]
    if item["source_type"] in ("x", "bluesky") and item["account"]:
        who = f"@{str(item['account']).lstrip('@')}"
    label = f"{who} ({kind})" if kind else who
    published = item["published_at"] or item["fetched_at"]
    return f"{label} · {humanize_age(now - published)}"


def _label(confidence: str, is_rumor: bool) -> str:
    return f"{confidence} · RUMOR" if is_rumor else confidence


def story_alert(story, items: Sequence, *, urgency: str, max_links: int = 3, now: float | None = None,
                muted: bool = False) -> Alert:
    """The first ring for a story. `items` = live (non-deleted) items, oldest first."""
    now = now or time.time()
    first = items[0]
    category = (story["category"] or first["category"]).upper()
    headline = truncate(story["headline"] or first["title"], 140)
    title = f"[{category}] [{_label(story['confidence'], bool(story['is_rumor']))}] {headline}"

    lines = [f"Summary: {story['summary']}" if story["summary"] else "Summary: (no summary — AI triage unavailable; raw headline above)"]
    if needs_death_warning(story["event_type"], story["confidence"]):
        lines.append(DEATH_WARNING)
    lines.append(f"Source: {source_line(first, now)}")
    others = _other_sources(items, max_links)
    link_names = ["original post", *[name for name, _ in others]] if first["url"] else [n for n, _ in others]
    if link_names:
        lines.append("Links: " + " · ".join(link_names))
    for name, url in others:
        lines.append(f"  {name}: {url}")
    if first["url"]:
        lines.append(f"  original: {first['url']}")
    if muted:
        lines.append("(muted — delivered without sound)")

    tags = [story["category"] or first["category"], story["event_type"] or "other"]
    if story["is_rumor"]:
        tags.append("rumor")
    return Alert(
        kind="ring",
        urgency="quiet" if muted else urgency,
        title=title,
        message="\n".join(lines),
        click_url=first["url"],
        links=others,
        tags=[t for t in tags if t],
        story_id=story["id"],
    )


def _other_sources(items: Sequence, limit: int) -> list[tuple[str, str]]:
    seen = {items[0]["source"]}
    out = []
    for it in items[1:]:
        if it["source"] in seen or not it["url"]:
            continue
        seen.add(it["source"])
        out.append((it["source"], it["url"]))
        if len(out) >= limit:
            break
    return out


def upgrade_alert(story, items: Sequence, new_sources: Iterable[str], *, max_links: int = 3) -> Alert:
    names = sorted(set(new_sources))
    first = items[0]
    headline = truncate(story["headline"] or first["title"], 120)
    title = f"[{(story['category'] or first['category']).upper()}] [{story['confidence']}] {headline}"
    others = _other_sources(items, max_links)
    lines = [f"Now {story['confidence'].lower()} by: {', '.join(names)}"]
    if story["summary"]:
        lines.append(f"Summary: {story['summary']}")
    for name, url in others:
        lines.append(f"  {name}: {url}")
    return Alert(
        kind="followup", urgency="quiet", title=title, message="\n".join(lines),
        click_url=first["url"], links=others, tags=["followup", "white_check_mark"], story_id=story["id"],
    )


def retraction_alert(story, retracted_item, remaining: Sequence, reason: str, *, louder: bool) -> Alert:
    headline = truncate(story["headline"] or retracted_item["title"], 120)
    title = f"[POSSIBLY FALSE] {headline}"
    lines = [
        f"{retracted_item['source']}: {reason}.",
        "This story may be false — check before acting.",
    ]
    if remaining:
        lines.append("Still reported by: " + ", ".join(sorted({r["source"] for r in remaining})))
    else:
        lines.append("No other sources report it.")
    return Alert(
        kind="retraction", urgency="normal" if louder else "quiet", title=title, message="\n".join(lines),
        click_url=retracted_item["url"], tags=["warning", "retraction"], story_id=story["id"],
    )


def health_alert(source: str, minutes: float, last_error: str | None) -> Alert:
    return Alert(
        kind="health", urgency="normal",
        title=f"[HEALTH] Watcher failing: {source}",
        message=f"No successful fetch from {source} for {minutes:.0f} min.\nLast error: {last_error or 'unknown'}",
        tags=["health", "warning"],
    )


def digest_alert(stories: Sequence, items_by_story: dict, *, reason: str, now: float | None = None) -> Alert:
    now = now or time.time()
    lines = []
    first_url = None
    for s in stories:
        items = items_by_story.get(s["id"]) or []
        url = items[0]["url"] if items else None
        first_url = first_url or url
        headline = truncate(s["headline"] or (items[0]["title"] if items else "?"), 110)
        lines.append(f"• [{(s['category'] or '?').upper()}] [{s['confidence']}] {headline}")
        if s["summary"]:
            lines.append(f"  {truncate(s['summary'], 160)}")
        if url:
            lines.append(f"  {url}")
    return Alert(
        kind="digest", urgency="normal",
        title=f"[DIGEST] {len(stories)} stor{'y' if len(stories) == 1 else 'ies'} {reason}",
        message="\n".join(lines), click_url=first_url, tags=["digest"],
    )
