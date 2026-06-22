from __future__ import annotations

from urllib.parse import urlencode

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.collectors.rss import parse_feed
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


def collect_arxiv(config: dict, raw_store: RawStore, now: str) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for query in config.get("queries", []):
        params = urlencode(
            {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": int(config.get("per_query", 10)),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        xml = fetch_bytes(f"https://export.arxiv.org/api/query?{params}")
        raw_path = raw_store.write_snapshot("arxiv", "xml", xml, now=now)
        for item in parse_feed(xml, source="arxiv", source_name="arXiv", raw_path=str(raw_path)):
            results.append(
                NormalizedItem(
                    source=item.source,
                    source_type="paper",
                    title=item.title,
                    url=item.url,
                    author=item.author,
                    published_at=item.published_at,
                    summary=item.summary,
                    raw_path=item.raw_path,
                    tags=["paper"],
                    metrics=item.metrics,
                    metadata=item.metadata,
                )
            )
    return results
