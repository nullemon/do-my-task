"""Fast, AI-free matching of watchlist names/aliases in headlines (English + Japanese)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .config import Watchlist, WatchlistEntry

_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
_KEY_STRIP = re.compile(r"[^\w]+")


def subject_key(name: str | None) -> str:
    """Normalize a subject/name for equality checks ("Spy × Family" == "spy x family")."""
    if not name:
        return ""
    v = unicodedata.normalize("NFKC", name).casefold().replace("×", "x")
    return _KEY_STRIP.sub("", v)


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


@dataclass(frozen=True)
class Match:
    entry: WatchlistEntry
    alias: str


class WatchlistIndex:
    def __init__(self, watchlist: Watchlist) -> None:
        self.entries = watchlist.entries
        self._by_key: dict[str, WatchlistEntry] = {}
        latin: dict[str, WatchlistEntry] = {}
        self._cjk: list[tuple[str, WatchlistEntry]] = []
        for entry in self.entries:
            for name in entry.all_names:
                name = unicodedata.normalize("NFKC", name).strip()
                if not name:
                    continue
                self._by_key.setdefault(subject_key(name), entry)
                if has_cjk(name):
                    if len(name) >= 2:
                        self._cjk.append((name, entry))
                elif len(name) >= 3:
                    latin.setdefault(name.casefold(), entry)
        self._latin = latin
        if latin:
            # Longest first so "Attack on Titan Final Season" beats "Attack on Titan".
            alts = sorted((re.escape(n) for n in latin), key=len, reverse=True)
            self._latin_re = re.compile(r"(?<![\w])(?:" + "|".join(alts) + r")(?![\w])", re.IGNORECASE)
        else:
            self._latin_re = None

    def __len__(self) -> int:
        return len(self.entries)

    def find(self, text: str) -> list[Match]:
        """All watchlist entries mentioned in `text` (deduplicated, in order of appearance)."""
        if not text:
            return []
        norm = unicodedata.normalize("NFKC", text)
        found: dict[str, Match] = {}
        if self._latin_re is not None:
            for m in self._latin_re.finditer(norm):
                entry = self._latin[m.group(0).casefold()]
                found.setdefault(entry.name, Match(entry, m.group(0)))
        for alias, entry in self._cjk:
            if alias in norm:
                found.setdefault(entry.name, Match(entry, alias))
        return list(found.values())

    def lookup(self, name: str | None) -> WatchlistEntry | None:
        """Exact (normalized) lookup of a subject name or alias."""
        if not name:
            return None
        return self._by_key.get(subject_key(name))

    def canonical(self, name: str | None) -> str:
        """Canonical subject key: maps aliases ("Shingeki no Kyojin") to the entry name."""
        entry = self.lookup(name)
        return subject_key(entry.name if entry else name)
