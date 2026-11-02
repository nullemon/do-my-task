"""Wikipedia watcher: Wikimedia EventStreams `recentchange` (SSE) + revert detection.

Every item is `trust: signal`. A Wikipedia edit is a hint that something
happened, never a confirmation.

Pages watched (English Wikipedia, article namespace, edits and page creations):

* "Deaths in <Month> <Year>" for the current month (UTC), plus last month's page
  for the first `deaths_previous_month_days` days, since late-announced deaths are
  filed under the month they happened, and "Deaths in <Year>". Titles are computed
  on every event, so they roll over at month and year change.
  For these, the diff is fetched (`action=compare`) and each newly added entry
  line becomes one item: `Deaths in November 2026: added "John Doe, 78, American
  actor (Show X)."`
* Every `wikipedia:` title in the watchlist (redirects are resolved once a week).
  Only non-bot edits whose added text looks like death, health, arrest or major
  news become an item (e.g. a `death_date` infobox field, `[[Category:2026
  deaths]]`, "is" -> "was" in a biography, words like died / arrested /
  hospitalized). The item's category comes from the watchlist entry.

Revert detection: each emitted edit is remembered for `revert_window_minutes`.
If a later edit on the page undoes, rolls back or restores past it (judged from
the edit summary), or MediaWiki tags the revision `mw-reverted` (checked every
`revert_check_seconds` via the API), we call `pipeline.retract(...)` so the
alert engine sends a "possibly false" follow-up. Nothing is retracted after the
window.

Wikimedia's policy requires a descriptive User-Agent with contact details; it is
taken from `polling.user_agent`.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable

import httpx

from ..config import Source, WatchlistEntry
from ..models import RawItem
from ..text import strip_html, truncate
from .base import RateLimited, SourceError, StreamWatcher, WatcherContext, _describe, load_json, parse_retry_after

log = logging.getLogger("newsalert.watcher.wikipedia")

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MAX_TEXT = 1500
_MAX_ENTRIES_PER_EDIT = 10  # more = a restructure or restore, not breaking news
_QUEUE_MAX = 500
_RETRY_DELAY_S = 5.0
_TAG_SETTLE_S = 15.0          # MediaWiki adds `mw-reverted` from a deferred job
_REDIRECT_CACHE_S = 7 * 86400
_EVENT_ID_KV = "wikipedia:last_event_id"
_PENDING_KV = "wikipedia:pending"
_REDIRECTS_KV = "wikipedia:redirects"


# --------------------------------------------------------------------------- titles


def normalize_title(title: str) -> str:
    """MediaWiki form: spaces not underscores, single spaces, first letter upper-case."""
    t = re.sub(r"\s+", " ", title.replace("_", " ")).strip()
    return t[:1].upper() + t[1:] if t else t


def deaths_titles(now: float, previous_month_days: int = 0) -> set[str]:
    dt = datetime.fromtimestamp(now, timezone.utc)
    titles = {f"Deaths in {MONTHS[dt.month - 1]} {dt.year}", f"Deaths in {dt.year}"}
    if dt.day <= previous_month_days:
        prev = dt.replace(day=1) - timedelta(days=1)
        titles.add(f"Deaths in {MONTHS[prev.month - 1]} {prev.year}")
        titles.add(f"Deaths in {prev.year}")
    return titles


def has_contact(user_agent: str) -> bool:
    """Wikimedia asks for contact info (email or URL) in the User-Agent."""
    return bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+|https?://|\bwww\.", user_agent or ""))


# --------------------------------------------------------------------------- SSE


@dataclass
class SseEvent:
    event: str
    data: str
    id: str | None = None


async def iter_sse(lines: AsyncIterator[str]) -> AsyncIterator[SseEvent]:
    """Minimal text/event-stream parser (event / data / id fields, comments ignored)."""
    event, data, event_id = "", [], None
    async for raw in lines:
        line = raw.rstrip("\r\n")
        if not line:
            if data:
                yield SseEvent(event or "message", "\n".join(data), event_id)
            event, data = "", []
            continue
        if line.startswith(":"):
            continue
        name, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if name == "event":
            event = value
        elif name == "data":
            data.append(value)
        elif name == "id":
            event_id = value
    if data:
        yield SseEvent(event or "message", "\n".join(data), event_id)


# --------------------------------------------------------------------------- diffs


@dataclass
class DiffRow:
    deleted: str | None = None   # old line (wikitext); None if the row only adds
    added: str | None = None     # new line (wikitext); None if the row only deletes
    dels: list[str] = field(default_factory=list)  # inline removed fragments (changed lines)
    ins: list[str] = field(default_factory=list)   # inline inserted fragments (changed lines)


_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td\b([^>]*)>(.*?)</td>", re.S | re.I)
_CLASS = re.compile(r'class\s*=\s*"([^"]*)"', re.I)
_INS = re.compile(r"<ins\b[^>]*>(.*?)</ins>", re.S | re.I)
_DEL = re.compile(r"<del\b[^>]*>(.*?)</del>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_MOVED_MARK = re.compile(r'<a\b[^>]*class="mw-diff-movedpara[^"]*"[^>]*>.*?</a>', re.S | re.I)


def _cell_text(fragment: str) -> str:
    # Real HTML tags first, then entities: escaped wikitext like &lt;ref&gt; survives.
    return html.unescape(_TAG.sub("", _MOVED_MARK.sub("", fragment))).strip()


def parse_diff(body: str) -> list[DiffRow]:
    """Rows of a MediaWiki `action=compare` HTML table diff."""
    rows = []
    for row in _ROW.finditer(body or ""):
        r = DiffRow()
        for attrs, inner in _CELL.findall(row.group(1)):
            m = _CLASS.search(attrs)
            cls = m.group(1) if m else ""
            if "diff-addedline" in cls:
                r.added = _cell_text(inner)
                r.ins = [t for t in (_cell_text(x) for x in _INS.findall(inner)) if t]
            elif "diff-deletedline" in cls:
                r.deleted = _cell_text(inner)
                r.dels = [t for t in (_cell_text(x) for x in _DEL.findall(inner)) if t]
        if r.added or r.deleted:
            rows.append(r)
    return rows


_TEMPLATE = re.compile(r"\{\{([^{}]*)\}\}")
_FIRST_ARG_TEMPLATES = {"ill", "interlanguage link", "nowrap", "nihongo", "nihongo2", "small", "abbr", "sic"}


def _expand_template(m: re.Match) -> str:
    parts = m.group(1).split("|")
    name = parts[0].strip().lower()
    positional = [p.strip() for p in parts[1:] if "=" not in p]
    if name in _FIRST_ARG_TEMPLATES and positional:
        return positional[0]
    if name == "lang" and len(positional) >= 2:
        return positional[1]
    if name == "sortname" and len(positional) >= 2:
        return f"{positional[0]} {positional[1]}"
    return ""


def wikitext_to_plain(text: str) -> str:
    s = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    s = re.sub(r"<ref\b[^>]*/\s*>", "", s, flags=re.I)
    s = re.sub(r"<ref\b[^>]*>.*?(?:</ref\s*>|$)", "", s, flags=re.I | re.S)
    for _ in range(6):  # innermost templates first
        s, n = _TEMPLATE.subn(_expand_template, s)
        if not n:
            break
    s = re.sub(r"\[\[\s*(?:Category|File|Image)\s*:[^\]]*\]\]", "", s, flags=re.I)
    s = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[https?://[^\s\]]+\s+([^\]]*)\]", r"\1", s)
    s = re.sub(r"\[https?://[^\]]*\]", "", s)
    s = re.sub(r"'{2,}", "", s)
    s = strip_html(s)
    return s.lstrip("*#:; ").strip()


_ENTRY = re.compile(r"^\*+\s*\[\[([^\]|]+)")


def _entry_key(line: str | None) -> str | None:
    m = _ENTRY.match((line or "").strip())
    return normalize_title(m.group(1)).lower() if m else None


def _norm_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def new_death_entries(rows: list[DiffRow]) -> list[str]:
    """Wikitext of entry lines (`*[[Name]], age, ...`) that this diff newly added.

    Moved lines and edits to an existing entry (fixing an age, adding a ref) are
    not new: they show the same line, or the same linked person, on the deleted side.
    """
    deleted = [r.deleted for r in rows if r.deleted]
    deleted_lines = {_norm_line(d) for d in deleted}
    deleted_keys = {k for d in deleted if (k := _entry_key(d))}
    out, seen = [], set()
    for r in rows:
        line = (r.added or "").strip()
        key = _entry_key(line)
        if not key or _norm_line(line) in deleted_lines or key in deleted_keys or key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


_DEATH_FIELDS = ("death_date", "death_place", "death_cause")
_DEATH_CATEGORY = re.compile(r"\[\[\s*Category\s*:\s*\d{4} deaths\b", re.I)
_DEATH_TEMPLATE = re.compile(r"\{\{\s*(?:death[ _-]date|death[ _-]year|dda)\b", re.I)
_WORD_SIGNALS = {
    "death": re.compile(
        r"\b(died|dies|passed away|(?:his|her|their) death|death of|was killed|were killed|killed in"
        r"|murdered|suicide|funeral)\b", re.I),
    "health": re.compile(
        r"\b(hospitali[sz]ed|hospitali[sz]ation|intensive care|critical condition|diagnosed with|cancer"
        r"|suffered a stroke|heart attack|underwent surgery|in a coma|seriously injured|(?:was|were) injured)\b", re.I),
    "legal": re.compile(
        r"\b(arrested|was charged|charged with|indicted|convicted|sentenced to|pleaded (?:not )?guilty"
        r"|filed a lawsuit|was sued)\b", re.I),
}
_MAJOR = re.compile(
    r"\b(hiatus|cancell?ed|discontinued|retired|retirement|disbanded|divorced?|went missing|reported missing"
    r"|final (?:chapter|season|episode|volume)|concluded|came to an end|(?:was|were|been) announced"
    r"|announced (?:a|an|the) (?:sequel|new season|second season|third season|film|anime adaptation))\b", re.I)


def _has_value(line: str | None, field_name: str) -> bool:
    return bool(line and re.search(rf"\|\s*{field_name}\s*=\s*[^\s|}}<]", line))


def watch_signals(rows: list[DiffRow], kind: str, year: int) -> tuple[list[str], str]:
    """Why an edit to a watchlist page matters (empty list = ignore it), plus a snippet."""
    deleted_lines = {_norm_line(r.deleted) for r in rows if r.deleted}
    new_lines: list[str] = []   # whole lines added (not moved)
    fragments: list[str] = []   # inline insertions in changed lines
    strong: list[str] = []
    for r in rows:
        if not r.added:
            continue
        if r.deleted is None:
            if _norm_line(r.added) not in deleted_lines:
                new_lines.append(r.added)
            continue
        fragments.extend(r.ins)
        for f in _DEATH_FIELDS:
            if _has_value(r.added, f) and not _has_value(r.deleted, f):
                strong.append(f)
        if kind == "person" and any(re.search(r"\bwas\b", t) for t in r.ins) and any(
            re.search(r"\bis\b", t) for t in r.dels
        ):
            strong.append('"is" -> "was"')
    raw = "\n".join(new_lines + fragments)
    for line in new_lines:
        strong.extend(f for f in _DEATH_FIELDS if _has_value(line, f))
    if _DEATH_CATEGORY.search(raw):
        strong.append("deaths category")
    if _DEATH_TEMPLATE.search(raw):
        strong.append("death date template")

    plain = wikitext_to_plain(raw)  # refs stripped: citation titles/dates don't count
    recent = re.search(rf"\b({year}|{year - 1})\b", plain) is not None
    words = []
    for rx in _WORD_SIGNALS.values():
        m = rx.search(plain)
        if m and (kind == "person" or recent):
            words.append(m.group(0).lower())
    m = _MAJOR.search(plain)
    if m and recent:
        words.append(m.group(0).lower())
    signals = list(dict.fromkeys(strong + words))

    snippet = plain
    field_lines = [ln.strip() for ln in new_lines + [r.added for r in rows if r.added and r.deleted is not None]
                   if any(_has_value(ln, f) for f in _DEATH_FIELDS)]
    if field_lines:
        snippet = " | ".join(p for p in [plain, *field_lines] if p)
    return signals, truncate(re.sub(r"\s+", " ", snippet).strip(), 400)


# --------------------------------------------------------------------------- reverts

_REVERT_WORDS = re.compile(
    r"\b(revert(?:ed|ing|s)?|rv|rvv|undid|undo|rollback|rolled back|restor(?:e|ed|ing))\b", re.I)
_UNDID = re.compile(r"\bundid revision (\d+)", re.I)
_RESTORED = re.compile(r"\b(?:restored|reverted to|revert to|rv to)\s+(?:revision|version|rev\.?)\s+(\d+)", re.I)


def is_revert_comment(comment: str | None) -> bool:
    return bool(comment and _REVERT_WORDS.search(comment))


def _mentions_user(comment: str, user: str) -> bool:
    u = re.escape(user.replace("_", " "))
    return bool(re.search(rf"(?:Special:Contrib(?:ution)?s/|User:|\bby ){u}(?:\||\]|\s|$|\)|:|,)", comment, re.I))


@dataclass
class Pending:
    revid: int
    page: str
    user: str
    external_ids: list[str]
    emitted_at: float


# --------------------------------------------------------------------------- watcher


class WikipediaWatcher(StreamWatcher):
    def __init__(self, source: Source, ctx: WatcherContext, *, clock: Callable[[], float] = time.time) -> None:
        super().__init__(ctx, [source], name=source.name, clock=clock)
        self.source = source
        self.cfg = ctx.settings.wikipedia
        self.watch_titles: dict[str, WatchlistEntry] = {}
        for entry in ctx.watchlist.entries:
            if entry.wikipedia:
                self.watch_titles.setdefault(normalize_title(entry.wikipedia), entry)
        self.pending: dict[int, Pending] = {}
        self.last_event_id: str | None = None
        self._saved_event_at = 0.0
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX)
        self._wake = asyncio.Event()
        self._deaths_cache: tuple[str, set[str]] = ("", set())
        self._load_state()

    # ------------------------------------------------------------------ main loops

    async def run(self) -> None:
        if not has_contact(self.ctx.settings.polling.user_agent):
            log.warning(
                "wikipedia.user_agent_without_contact",
                extra={"hint": "put an email or URL in settings.yaml polling.user_agent (Wikimedia User-Agent policy)"},
            )
        try:
            await self.resolve_redirects()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("wikipedia.redirects_failed", extra={"error": _describe(exc)})
        await asyncio.gather(super().run(), self._worker(), self._sweeper())

    async def connect_once(self) -> None:
        headers = {"Accept": "text/event-stream", "User-Agent": self.ctx.settings.polling.user_agent}
        if self.last_event_id:
            headers["Last-Event-ID"] = self.last_event_id
        timeout = httpx.Timeout(15.0, read=self.cfg.read_timeout)
        async with self.ctx.client.stream("GET", self.cfg.stream_url, headers=headers, timeout=timeout) as resp:
            if resp.status_code in (429, 503):
                raise RateLimited(parse_retry_after(resp.headers.get("retry-after")), f"HTTP {resp.status_code}")
            resp.raise_for_status()
            self.connected()
            log.info("wikipedia.connected", extra={"resumed": bool(self.last_event_id), "watch_pages": len(self.watch_titles)})
            async for event in iter_sse(resp.aiter_lines()):
                if event.id:
                    self.last_event_id = event.id
                    self._save_event_id()
                self.alive()
                if event.event != "message" or not event.data:
                    continue
                try:
                    change = json.loads(event.data)
                except ValueError:
                    continue
                await self.handle_change(change)

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            await self._run_job(job)

    async def drain(self) -> None:
        """Process everything queued (used by tests and on shutdown paths)."""
        while not self._queue.empty():
            await self._run_job(self._queue.get_nowait())

    async def _sweeper(self) -> None:
        while True:
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.cfg.revert_check_seconds)
                woke = True
            except TimeoutError:
                woke = False
            self._wake.clear()
            if woke:
                await asyncio.sleep(_TAG_SETTLE_S)
            try:
                await self.check_reverts_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("wikipedia.revert_check_failed", extra={"error": _describe(exc)})

    # ------------------------------------------------------------------ events

    def current_deaths_titles(self, now: float) -> set[str]:
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        if self._deaths_cache[0] != day:
            self._deaths_cache = (day, deaths_titles(now, self.cfg.deaths_previous_month_days))
        return self._deaths_cache[1]

    def classify(self, title: str, now: float) -> tuple[str, WatchlistEntry | None] | None:
        if title in self.current_deaths_titles(now):
            return "deaths", None
        entry = self.watch_titles.get(title)
        return ("watch", entry) if entry is not None else None

    async def handle_change(self, change: Any) -> None:
        """One recentchange event from the stream."""
        if not isinstance(change, dict) or change.get("wiki") != self.cfg.wiki:
            return
        title = change.get("title")
        if not isinstance(title, str):
            return
        now = self.clock()
        if any(p.page == title for p in self.pending.values()):
            await self._check_revert_event(change, now)
        if change.get("type") not in ("edit", "new") or change.get("namespace") != 0:
            return
        target = self.classify(title, now)
        if target is None:
            return
        kind, entry = target
        if kind == "watch" and change.get("bot"):
            return
        if is_revert_comment(change.get("comment")):
            return  # restores old text; whatever it "adds" was there before
        try:
            self._queue.put_nowait((kind, entry, change))
        except asyncio.QueueFull:
            log.warning("wikipedia.queue_full", extra={"title": title})

    async def _run_job(self, job: tuple) -> None:
        kind, entry, change = job
        for attempt in (1, 2):
            try:
                await self.process(kind, entry, change)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if attempt == 2:
                    log.warning("wikipedia.diff_failed", extra={"title": change.get("title"), "error": _describe(exc)})
                    return
                await asyncio.sleep(_RETRY_DELAY_S)

    async def process(self, kind: str, entry: WatchlistEntry | None, change: dict) -> list[RawItem]:
        """Fetch the diff of one edit and turn it into items (possibly none)."""
        rev = change.get("revision") or {}
        new, old = rev.get("new"), rev.get("old")
        if not isinstance(new, int):
            return []
        rows = await self.fetch_diff(old if isinstance(old, int) else None, new)
        now = self.clock()
        title = change["title"]
        link = self.diff_link(change, old, new)
        published = change.get("timestamp") if isinstance(change.get("timestamp"), (int, float)) else None
        user = change.get("user") or None
        wiki = self.cfg.wiki
        items: list[RawItem] = []
        if kind == "deaths":
            src = self._item_source("celebrity")
            entries = new_death_entries(rows)
            if len(entries) > _MAX_ENTRIES_PER_EDIT:
                log.info("wikipedia.bulk_edit_skipped", extra={"title": title, "revid": new, "entries": len(entries)})
                entries = []
            for n, line in enumerate(entries, 1):
                plain = wikitext_to_plain(line)
                if not plain:
                    continue
                text = f'{title}: added "{plain}"'
                items.append(RawItem.from_source(
                    src,
                    # One diff can add several people; the unique-URL index needs distinct
                    # links, so later entries get a harmless extra parameter.
                    url=link if n == 1 else f"{link}&entry={n}",
                    account=user,
                    external_id=f"{wiki}:{new}:{n}",
                    title=truncate(text, 200),
                    text=truncate(text, _MAX_TEXT),
                    published_at=published,
                    fetched_at=now,
                ))
        elif entry is not None:
            year = datetime.fromtimestamp(now, timezone.utc).year
            signals, snippet = watch_signals(rows, entry.kind, year)
            if not signals:
                return []
            summary = wikitext_to_plain(change.get("comment") or "")
            text = f'Wikipedia edit on "{title}" ({entry.name}): added "{snippet}".'
            if summary:
                text += f" Edit summary: {summary}."
            text += f" Signals: {', '.join(signals)}."
            items.append(RawItem.from_source(
                self._item_source(entry.category),
                url=link,
                account=user,
                external_id=f"{wiki}:{new}",
                title=truncate(f"{title} (Wikipedia): {snippet or ', '.join(signals)}", 200),
                text=truncate(text, _MAX_TEXT),
                published_at=published,
                fetched_at=now,
            ))
        if items:
            await self.ctx.pipeline.ingest(self.source, items, seeding=False)
            self.pending[new] = Pending(new, title, user or "", [i.external_id for i in items], now)
            self._save_pending()
            log.info("wikipedia.emitted", extra={"title": title, "revid": new, "items": len(items), "kind": kind})
        return items

    def _item_source(self, category: str) -> Source:
        # Wikipedia is never confirmation, whatever sources.yaml says.
        return self.source.model_copy(update={"category": category, "trust": "signal"})

    @staticmethod
    def diff_link(change: dict, old: Any, new: int) -> str:
        server = change.get("server_url") or "https://en.wikipedia.org"
        if isinstance(old, int) and old:
            return f"{server}/w/index.php?diff={new}&oldid={old}"
        return f"{server}/w/index.php?oldid={new}"

    # ------------------------------------------------------------------ API

    async def api(self, **params: Any) -> dict:
        resp = await self.ctx.client.get(
            self.cfg.api_url,
            params={"format": "json", "formatversion": "2", **params},
            headers={"User-Agent": self.ctx.settings.polling.user_agent},
        )
        if resp.status_code in (429, 503):
            raise RateLimited(parse_retry_after(resp.headers.get("retry-after")), f"HTTP {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            raise SourceError(f"API error {data['error'].get('code')}")
        return data

    async def fetch_diff(self, old: int | None, new: int) -> list[DiffRow]:
        if not old:  # page creation: every line is new
            data = await self.api(action="query", prop="revisions", revids=new, rvprop="content", rvslots="main")
            pages = (data.get("query") or {}).get("pages") or []
            revs = pages[0].get("revisions") if pages else None
            content = ((revs or [{}])[0].get("slots") or {}).get("main", {}).get("content", "")
            return [DiffRow(added=line) for line in content.splitlines() if line.strip()]
        data = await self.api(action="compare", fromrev=old, torev=new, prop="diff")
        compare = data.get("compare") or {}
        return parse_diff(compare.get("body") or compare.get("*") or "")

    async def resolve_redirects(self) -> None:
        """Watch the target too when a watchlist title is a redirect (cached a week)."""
        now = self.clock()
        cached = load_json(self.ctx.db.kv_get(_REDIRECTS_KV))
        if cached and now - float(cached.get("at") or 0) < _REDIRECT_CACHE_S:
            mapping = cached.get("map") or {}
        else:
            mapping = {}
            titles = list(self.watch_titles)
            for i in range(0, len(titles), 50):
                batch = titles[i:i + 50]
                data = await self.api(action="query", titles="|".join(batch), redirects="1")
                query = data.get("query") or {}
                norm = {n["from"]: n["to"] for n in query.get("normalized") or []}
                redir = {r["from"]: r["to"] for r in query.get("redirects") or []}
                for t in batch:
                    target = redir.get(norm.get(t, t), norm.get(t, t))
                    if target != t:
                        mapping[t] = target
            self.ctx.db.kv_set(_REDIRECTS_KV, json.dumps({"at": now, "map": mapping}))
        for original, target in mapping.items():
            entry = self.watch_titles.get(original)
            if entry is not None:
                self.watch_titles.setdefault(normalize_title(target), entry)
        if mapping:
            log.info("wikipedia.redirects", extra={"resolved": len(mapping)})

    # ------------------------------------------------------------------ reverts

    def _window_s(self) -> float:
        return self.cfg.revert_window_minutes * 60

    async def _check_revert_event(self, change: dict, now: float) -> None:
        """A later edit on a page we emitted from: does its summary say ours was undone?"""
        comment = (change.get("comment") or "").replace("_", " ")
        new_rev = (change.get("revision") or {}).get("new")
        undid = [int(x) for x in _UNDID.findall(comment)]
        restored = [int(x) for x in _RESTORED.findall(comment)]
        if not (undid or restored or _REVERT_WORDS.search(comment)):
            return
        title = change.get("title")
        candidates = [
            p for p in list(self.pending.values())
            if p.page == title and (not isinstance(new_rev, int) or new_rev > p.revid)
        ]
        for p in candidates:
            if now - p.emitted_at > self._window_s():
                continue
            if undid:
                hit = p.revid in undid
            elif restored:
                hit = any(r < p.revid for r in restored)
            else:
                hit = bool(p.user) and _mentions_user(comment, p.user)
            if hit:
                await self._retract(p, "wikipedia edit reverted")
            else:
                self._wake.set()  # unclear summary: let the tag check decide soon

    async def check_reverts_once(self) -> None:
        """Ask the API whether any remembered revision is now tagged `mw-reverted`."""
        now = self.clock()
        expired = [r for r, p in self.pending.items() if now - p.emitted_at > self._window_s()]
        for revid in expired:
            del self.pending[revid]
        if expired:
            self._save_pending()
        revids = sorted(self.pending)
        for i in range(0, len(revids), 50):
            batch = revids[i:i + 50]
            data = await self.api(action="query", prop="revisions", revids="|".join(map(str, batch)), rvprop="ids|tags")
            for page in (data.get("query") or {}).get("pages") or []:
                for rev in page.get("revisions") or []:
                    p = self.pending.get(rev.get("revid"))
                    if p is not None and "mw-reverted" in (rev.get("tags") or []):
                        if self.clock() - p.emitted_at <= self._window_s():
                            await self._retract(p, "wikipedia edit reverted")

    async def _retract(self, p: Pending, reason: str) -> None:
        self.pending.pop(p.revid, None)
        self._save_pending()
        log.info("wikipedia.revert_detected", extra={"title": p.page, "revid": p.revid})
        for external_id in p.external_ids:
            await self.ctx.pipeline.retract(self.source.name, external_id, reason)

    # ------------------------------------------------------------------ persistence

    def _load_state(self) -> None:
        now = self.clock()
        data = load_json(self.ctx.db.kv_get(_EVENT_ID_KV))
        max_age = self.ctx.settings.pipeline.stale_minutes * 60
        if data and data.get("id") and now - float(data.get("at") or 0) <= max_age:
            self.last_event_id = data["id"]  # resume after a short restart; older = stale anyway
        raw = self.ctx.db.kv_get(_PENDING_KV)
        try:
            entries = json.loads(raw) if raw else []
        except ValueError:
            entries = []
        for e in entries if isinstance(entries, list) else []:
            try:
                p = Pending(**e)
            except TypeError:
                continue
            if now - p.emitted_at <= self._window_s():
                self.pending[p.revid] = p

    def _save_event_id(self) -> None:
        now = self.clock()
        if now - self._saved_event_at >= 10:
            self._saved_event_at = now
            self.ctx.db.kv_set(_EVENT_ID_KV, json.dumps({"id": self.last_event_id, "at": now}))

    def _save_pending(self) -> None:
        self.ctx.db.kv_set(_PENDING_KV, json.dumps([asdict(p) for p in self.pending.values()]))
