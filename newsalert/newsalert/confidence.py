"""Source-based confidence labels. No AI: computed only from who reported the story.

  OFFICIAL SOURCE  at least one `official` source (family, agency, studio, publisher, verified rep)
  CONFIRMED        two independent `major` outlets, or official + major
  SINGLE OUTLET    `major` source(s) from a single ownership group only
  UNCONFIRMED      only `signal` sources (Wikipedia edits, fan/aggregator accounts)

`signal` sources never count towards confirmation. Two outlets with the same
`group` (e.g. Variety + Deadline, both Penske Media) are one outlet here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

CONFIRMED = "CONFIRMED"
OFFICIAL = "OFFICIAL SOURCE"
SINGLE = "SINGLE OUTLET"
UNCONFIRMED = "UNCONFIRMED"

RANK = {UNCONFIRMED: 0, SINGLE: 1, OFFICIAL: 2, CONFIRMED: 3}

DEATH_WARNING = "Not confirmed — check before acting."


@dataclass(frozen=True)
class SourceRef:
    name: str
    trust: str   # official | major | signal
    group: str


def label_for(sources: Iterable[SourceRef]) -> str:
    sources = list(sources)
    official = {s.group for s in sources if s.trust == "official"}
    major = {s.group for s in sources if s.trust == "major"}
    if (official and major) or len(major) >= 2:
        return CONFIRMED
    if official:
        return OFFICIAL
    if major:
        return SINGLE
    return UNCONFIRMED


def needs_death_warning(event_type: str | None, label: str) -> bool:
    return event_type == "death" and label == UNCONFIRMED


def is_upgrade(old: str | None, new: str) -> bool:
    return old is None or RANK[new] > RANK.get(old, -1)
