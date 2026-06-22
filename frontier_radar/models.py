from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any


def stable_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class NormalizedItem:
    source: str
    source_type: str
    title: str
    url: str
    author: str
    published_at: str
    summary: str
    raw_path: str
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, int | float | str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def item_id(self) -> str:
        return stable_id(self.url)

    def to_record(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source": self.source,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at,
            "summary": self.summary,
            "raw_path": self.raw_path,
            "tags": list(self.tags),
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, order=True)
class ScoredItem:
    score: float
    item_id: str = field(compare=False)
    components: dict[str, float] = field(default_factory=dict, compare=False)
