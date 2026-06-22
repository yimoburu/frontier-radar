from __future__ import annotations

import json
from urllib.parse import urlencode

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


def parse_hn_search(payload: dict, raw_path: str) -> list[NormalizedItem]:
    items: list[NormalizedItem] = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title") or ""
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        items.append(
            NormalizedItem(
                source="hn",
                source_type="discussion",
                title=title,
                url=url,
                author=hit.get("author") or "",
                published_at=hit.get("created_at") or "1970-01-01T00:00:00+00:00",
                summary=title,
                raw_path=raw_path,
                tags=["discussion"],
                metrics={"points": hit.get("points") or 0, "comments": hit.get("num_comments") or 0},
                metadata={"object_id": hit.get("objectID")},
            )
        )
    return [item for item in items if item.url and item.title]


def collect_hn(
    config: dict,
    raw_store: RawStore,
    now: str,
    errors: list[str] | None = None,
) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for query in config.get("queries", []):
        try:
            params = urlencode({"query": query, "tags": "story", "hitsPerPage": int(config.get("per_query", 10))})
            raw = fetch_bytes(f"https://hn.algolia.com/api/v1/search_by_date?{params}")
            raw_path = raw_store.write_snapshot("hn", "json", raw, now=now)
            results.extend(parse_hn_search(json.loads(raw.decode("utf-8")), str(raw_path)))
        except Exception as exc:
            if errors is not None:
                errors.append(f"hn query {query}: {exc}")
            continue
    return results
