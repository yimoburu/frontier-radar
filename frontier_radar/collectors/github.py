from __future__ import annotations

import json
from urllib.parse import urlencode

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


def parse_github_search(payload: dict, raw_path: str) -> list[NormalizedItem]:
    items: list[NormalizedItem] = []
    for repo in payload.get("items", []):
        language = repo.get("language") or "unknown"
        items.append(
            NormalizedItem(
                source="github",
                source_type="repo",
                title=repo.get("full_name", ""),
                url=repo.get("html_url", ""),
                author=repo.get("owner", {}).get("login", ""),
                published_at=repo.get("updated_at") or repo.get("created_at") or "1970-01-01T00:00:00+00:00",
                summary=repo.get("description") or "",
                raw_path=raw_path,
                tags=[language],
                metrics={
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                },
                metadata={"created_at": repo.get("created_at"), "language": language},
            )
        )
    return [item for item in items if item.url and item.title]


def collect_github(
    config: dict,
    raw_store: RawStore,
    now: str,
    errors: list[str] | None = None,
) -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for query in config.get("queries", []):
        try:
            params = urlencode(
                {
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": int(config.get("per_query", 10)),
                }
            )
            raw = fetch_bytes(f"https://api.github.com/search/repositories?{params}")
            raw_path = raw_store.write_snapshot("github", "json", raw, now=now)
            results.extend(parse_github_search(json.loads(raw.decode("utf-8")), str(raw_path)))
        except Exception as exc:
            if errors is not None:
                errors.append(f"github query {query}: {exc}")
            continue
    return results
