from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
from typing import Any

from frontier_radar.models import NormalizedItem


MOMENTUM_KEYS = ("stars", "points", "comments", "score", "views")
FRESHNESS_WINDOW_HOURS = 168


@dataclass(frozen=True)
class RankedItem:
    item: NormalizedItem
    score: float
    components: dict[str, float]


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def freshness_score(published_at: str, now: str | datetime | None = None) -> float:
    published = parse_time(published_at)
    current = _coerce_now(now)
    age_hours = max(0.0, (current - published).total_seconds() / 3600)
    return max(0.0, 1.0 - (age_hours / FRESHNESS_WINDOW_HOURS))


def momentum_score(metrics: dict[str, int | float | str]) -> float:
    total = 0.0
    for key in MOMENTUM_KEYS:
        total += _numeric_metric(metrics.get(key, 0))
    return min(4.0, math.log10(total + 1))


def relevance_score(item: NormalizedItem, topics: dict[str, Any]) -> float:
    text = " ".join([item.title, item.summary, *item.tags]).casefold()
    hits = 0
    for topic in topics.get("topics", {}).values():
        for keyword in topic.get("keywords", []):
            if str(keyword).casefold() in text:
                hits += 1
    return float(hits)


def score_item(
    item: NormalizedItem,
    topics: dict[str, Any],
    now: str | datetime | None = None,
) -> RankedItem:
    components = {
        "freshness": freshness_score(item.published_at, now=now),
        "momentum": momentum_score(item.metrics),
        "relevance": relevance_score(item, topics),
    }
    return RankedItem(item=item, score=sum(components.values()), components=components)


def rank_items(
    items: list[NormalizedItem],
    topics: dict[str, Any],
    now: str | datetime | None = None,
    limit: int | None = None,
) -> list[RankedItem]:
    ranked = [score_item(item, topics, now=now) for item in items]
    ranked.sort(key=lambda scored: (-scored.score, scored.item.title))
    if limit is None:
        return ranked
    return ranked[:limit]


def _coerce_now(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return parse_time(value)


def _numeric_metric(value: int | float | str | None) -> float:
    try:
        metric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, metric)
