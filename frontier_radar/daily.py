from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from frontier_radar.collectors.arxiv import collect_arxiv
from frontier_radar.collectors.github import collect_github
from frontier_radar.collectors.hn import collect_hn
from frontier_radar.collectors.manual import collect_manual_notes
from frontier_radar.collectors.rss import collect_rss
from frontier_radar.config import load_app_config
from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import rank_items
from frontier_radar.raw import RawStore
from frontier_radar.storage import Database
from frontier_radar.wiki.render import write_daily_digest


@dataclass(frozen=True)
class DailyResult:
    status: str
    digest_path: Path
    counts: dict[str, int]
    errors: list[str]
    top_titles: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def collect_all(
    root: Path,
    raw_store: RawStore,
    sources: dict,
    now: str,
    live_network: bool,
) -> tuple[list[NormalizedItem], dict[str, int], list[str]]:
    items: list[NormalizedItem] = []
    counts: dict[str, int] = {}
    errors: list[str] = []

    manual_config = sources.get("manual", {})
    if manual_config.get("enabled", False):
        try:
            manual_items = collect_manual_notes(root, manual_config.get("directory", "manual"))
            items.extend(manual_items)
            counts["manual"] = len(manual_items)
        except Exception as exc:
            counts["manual"] = 0
            errors.append(f"manual: {exc}")

    if not live_network:
        return items, counts, errors

    collectors = []
    if sources.get("github", {}).get("enabled", False):
        collectors.append(
            (
                "github",
                lambda: collect_github(sources["github"], raw_store, now, errors=errors),
            )
        )
    if sources.get("hn", {}).get("enabled", False):
        collectors.append(
            (
                "hn",
                lambda: collect_hn(sources["hn"], raw_store, now, errors=errors),
            )
        )
    if sources.get("arxiv", {}).get("enabled", False):
        collectors.append(
            (
                "arxiv",
                lambda: collect_arxiv(sources["arxiv"], raw_store, now, errors=errors),
            )
        )
    if sources.get("rss", {}).get("enabled", False):
        collectors.append(
            (
                "rss",
                lambda: collect_rss(sources["rss"], raw_store, now, source="rss", errors=errors),
            )
        )
    youtube_config = sources.get("youtube", {})
    if youtube_config.get("enabled", False) and youtube_config.get("channel_feeds"):
        collectors.append(
            (
                "youtube",
                lambda: collect_rss(
                    {"feeds": youtube_config["channel_feeds"]},
                    raw_store,
                    now,
                    source="youtube",
                    errors=errors,
                ),
            )
        )

    for source, collect in collectors:
        before_errors = len(errors)
        try:
            collected = collect()
        except Exception as exc:
            counts[source] = 0
            errors.append(f"{source}: {exc}")
            continue
        items.extend(collected)
        counts[source] = len(collected)
        if len(errors) > before_errors and source not in counts:
            counts[source] = len(collected)

    return items, counts, errors


def run_daily(root: Path, now: str | None = None, live_network: bool = True) -> DailyResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()

    raw_store = RawStore(root)
    items, counts, errors = collect_all(root, raw_store, config.sources, started_at, live_network)
    db.upsert_items(items)

    ranked = rank_items(db.list_items(), config.topics, now=started_at, limit=20)
    digest_path = write_daily_digest(root, started_at[:10], ranked, counts, errors)
    status = _status(items, errors)
    db.record_run(
        started_at=started_at,
        finished_at=utc_now_iso(),
        status=status,
        counts=counts,
        errors=errors,
        outputs=[str(digest_path)],
    )

    return DailyResult(
        status=status,
        digest_path=digest_path,
        counts=counts,
        errors=errors,
        top_titles=[entry.item.title for entry in ranked[:5]],
    )


def _status(items: list[NormalizedItem], errors: list[str]) -> str:
    if not errors:
        return "ok"
    if items:
        return "partial"
    return "error"
