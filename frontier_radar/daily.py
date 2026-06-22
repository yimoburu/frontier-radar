from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time

from frontier_radar.collectors.arxiv import collect_arxiv
from frontier_radar.collectors.github import collect_github
from frontier_radar.collectors.hn import collect_hn
from frontier_radar.collectors.manual import collect_manual_notes
from frontier_radar.collectors.rss import collect_rss
from frontier_radar.config import effective_job_config, load_app_config, load_jobs_config
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


@dataclass(frozen=True)
class FetchResult:
    status: str
    counts: dict[str, int]
    errors: list[str]
    item_count: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def collect_all(
    root: Path,
    raw_store: RawStore,
    sources: dict,
    now: str,
    live_network: bool,
    only_sources: set[str] | None = None,
    deadline: float | None = None,
) -> tuple[list[NormalizedItem], dict[str, int], list[str]]:
    items: list[NormalizedItem] = []
    counts: dict[str, int] = {}
    errors: list[str] = []

    manual_config = sources.get("manual", {})
    if manual_config.get("enabled", False) and _source_selected("manual", only_sources):
        try:
            manual_items = collect_manual_notes(
                root,
                manual_config.get("directory", "manual"),
                errors=errors,
            )
            items.extend(manual_items)
            counts["manual"] = len(manual_items)
        except Exception as exc:
            counts["manual"] = 0
            errors.append(f"manual: {exc}")

    if not live_network:
        return items, counts, errors

    collectors = []
    if sources.get("github", {}).get("enabled", False) and _source_selected("github", only_sources):
        collectors.append(
            (
                "github",
                lambda: collect_github(sources["github"], raw_store, now, errors=errors),
            )
        )
    if sources.get("hn", {}).get("enabled", False) and _source_selected("hn", only_sources):
        collectors.append(
            (
                "hn",
                lambda: collect_hn(sources["hn"], raw_store, now, errors=errors),
            )
        )
    if sources.get("arxiv", {}).get("enabled", False) and _source_selected("arxiv", only_sources):
        collectors.append(
            (
                "arxiv",
                lambda: collect_arxiv(sources["arxiv"], raw_store, now, errors=errors),
            )
        )
    if sources.get("rss", {}).get("enabled", False) and _source_selected("rss", only_sources):
        collectors.append(
            (
                "rss",
                lambda: collect_rss(sources["rss"], raw_store, now, source="rss", errors=errors),
            )
        )
    youtube_config = sources.get("youtube", {})
    if (
        youtube_config.get("enabled", False)
        and youtube_config.get("channel_feeds")
        and _source_selected("youtube", only_sources)
    ):
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
        if deadline is not None and time.monotonic() >= deadline:
            counts[source] = 0
            errors.append(f"{source}: time budget exhausted")
            continue
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


def fetch_once(root: Path, now: str | None = None, live_network: bool = True) -> FetchResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()

    raw_store = RawStore(root)
    items, counts, errors = collect_all(root, raw_store, config.sources, started_at, live_network)
    items = _dedupe_items(items)
    db.upsert_items(items)
    status = _status(items, errors)
    db.record_run(
        started_at=started_at,
        finished_at=utc_now_iso(),
        status=status,
        counts=counts,
        errors=errors,
        outputs=[],
    )
    return FetchResult(status=status, counts=counts, errors=errors, item_count=len(items))


def run_daily(
    root: Path,
    now: str | None = None,
    live_network: bool = True,
    budget_minutes: int | None = None,
    top_n: int | None = None,
) -> DailyResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    jobs_config = load_jobs_config(root / "config" / "jobs.yaml")
    effective_config = effective_job_config(
        jobs_config,
        "daily",
        {"budget_minutes": budget_minutes, "top_n": top_n},
    )
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()

    items: list[NormalizedItem] = []
    counts: dict[str, int] = {}
    errors: list[str] = []
    ranked = []
    digest_path = Path("wiki") / "daily" / f"{started_at[:10]}.md"
    source_statuses: dict[str, dict] = {}
    lock_acquired = False

    if effective_config.get("prevent_overlapping_runs", True):
        lock_acquired = db.acquire_lock(
            "pipeline",
            "daily",
            started_at,
            int(effective_config.get("stale_run_after_minutes", 60)),
        )
        if not lock_acquired:
            errors = ["active lock prevents daily run"]
            run_id = db.record_run(
                started_at=started_at,
                finished_at=utc_now_iso(),
                status="locked",
                counts={},
                errors=errors,
                outputs=[],
                job_type="daily",
                effective_config=effective_config,
            )
            return DailyResult(
                status="locked",
                digest_path=digest_path,
                counts={},
                errors=errors,
                top_titles=[],
            )

    try:
        seen_item_ids = db.item_ids()
        raw_store = RawStore(root)
        deadline = time.monotonic() + (float(effective_config["budget_minutes"]) * 60)
        items, counts, errors = collect_all(
            root,
            raw_store,
            config.sources,
            started_at,
            live_network,
            deadline=deadline,
        )
        items = _dedupe_items(items)
        db.upsert_items(items)
        source_statuses = _source_statuses(config.sources, counts, errors)

        ranked = rank_items(
            items,
            config.topics,
            now=started_at,
            limit=int(effective_config["top_n"]),
            seen_item_ids=seen_item_ids,
        )
        digest_path = write_daily_digest(root, started_at[:10], ranked, counts, errors)
    except Exception as exc:
        errors.append(f"daily pipeline: {exc}")
        source_statuses = _source_statuses(config.sources, counts, errors)
        try:
            digest_path = write_daily_digest(root, started_at[:10], [], counts, errors)
        except Exception as render_exc:
            errors.append(f"digest render: {render_exc}")
            source_statuses = _source_statuses(config.sources, counts, errors)
    finally:
        if lock_acquired:
            db.release_lock("pipeline")

    status = _status(items, errors)
    run_id = db.record_run(
        started_at=started_at,
        finished_at=utc_now_iso(),
        status=status,
        counts=counts,
        errors=errors,
        outputs=[str(digest_path)],
        job_type="daily",
        effective_config=effective_config,
    )
    _record_source_statuses(db, run_id, source_statuses)

    return DailyResult(
        status=status,
        digest_path=digest_path,
        counts=counts,
        errors=errors,
        top_titles=[entry.item.title for entry in ranked[:5]],
    )


def _status(items: list[NormalizedItem], errors: list[str]) -> str:
    if errors and any(error.startswith("daily pipeline:") or error.startswith("digest render:") for error in errors):
        return "error"
    if not errors:
        return "ok"
    if items:
        return "partial"
    return "error"


def _dedupe_items(items: list[NormalizedItem]) -> list[NormalizedItem]:
    seen: set[str] = set()
    unique: list[NormalizedItem] = []
    for item in items:
        if item.item_id in seen:
            continue
        seen.add(item.item_id)
        unique.append(item)
    return unique


def _source_selected(source: str, only_sources: set[str] | None) -> bool:
    return only_sources is None or source in only_sources


def _record_source_statuses(db: Database, run_id: int, statuses: dict[str, dict]) -> None:
    for source, status in statuses.items():
        db.record_source_run(
            run_id=run_id,
            source=source,
            status=status["status"],
            count=status["count"],
            error=status["error"],
            retry_eligible=status["retry_eligible"],
        )


def _source_statuses(
    sources: dict,
    counts: dict[str, int],
    errors: list[str],
    only_sources: set[str] | None = None,
) -> dict[str, dict]:
    statuses: dict[str, dict] = {}
    for source, settings in sorted(sources.items()):
        if not settings.get("enabled", False):
            continue
        if only_sources is not None and source not in only_sources:
            statuses[source] = {
                "status": "skipped",
                "count": 0,
                "error": "",
                "retry_eligible": False,
            }
            continue
        source_errors = [error for error in errors if _error_matches_source(error, source)]
        count = int(counts.get(source, 0))
        if source_errors and count > 0:
            status = "partial"
        elif source_errors:
            status = "timeout" if any("timeout" in error.casefold() or "budget" in error.casefold() for error in source_errors) else "failed"
        elif source in counts:
            status = "success"
        else:
            status = "skipped"
        statuses[source] = {
            "status": status,
            "count": count,
            "error": "; ".join(source_errors),
            "retry_eligible": status in {"partial", "failed", "timeout"},
        }
    return statuses


def _error_matches_source(error: str, source: str) -> bool:
    return (
        error == source
        or error.startswith(f"{source}:")
        or error.startswith(f"{source} ")
        or error.startswith(f"{source} query")
        or error.startswith(f"{source} feed")
        or error.startswith(f"{source} note")
    )
