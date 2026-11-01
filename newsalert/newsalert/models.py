"""Data passed between watchers and the pipeline."""

from __future__ import annotations

from pydantic import BaseModel

from .config import Category, Source, SourceType, Trust


class RawItem(BaseModel):
    """One post/article exactly as a watcher saw it. No AI involved."""

    source: str
    source_type: SourceType
    category: Category
    trust: Trust
    source_group: str
    url: str | None = None
    account: str | None = None
    external_id: str | None = None
    title: str
    text: str
    published_at: float | None = None  # unix seconds, UTC; None if the source gave no date
    fetched_at: float

    @classmethod
    def from_source(cls, source: Source, **fields) -> "RawItem":
        return cls(
            source=source.name,
            source_type=source.type,
            category=source.category,
            trust=source.trust,
            source_group=source.independence_group,
            **fields,
        )
