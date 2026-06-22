from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from typing import Any

from frontier_radar.config import effective_job_config, load_app_config, load_jobs_config
from frontier_radar.daily import (
    _dedupe_items,
    _source_statuses,
    collect_all,
    utc_now_iso,
)
from frontier_radar.ranking import rank_items
from frontier_radar.raw import RawStore
from frontier_radar.storage import Database
from frontier_radar.wiki.lint import lint_wiki


@dataclass(frozen=True)
class JobResult:
    job_type: str
    status: str
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    item_count: int = 0


@dataclass(frozen=True)
class HealthResult:
    status: str
    issues: list[str]
    cleaned_locks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VacuumResult:
    status: str
    cleaned_locks: list[str]


def run_retry_failed(
    root: Path,
    now: str | None = None,
    since: str | None = None,
    budget_minutes: int | None = None,
) -> JobResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    app_config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    jobs_config = load_jobs_config(root / "config" / "jobs.yaml")
    effective_config = effective_job_config(
        jobs_config,
        "retry_failed",
        {"budget_minutes": budget_minutes, "retry_window": since},
    )
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()

    if not db.acquire_lock("pipeline", "retry_failed", started_at, int(effective_config.get("budget_minutes", 10))):
        errors = ["active lock prevents retry run"]
        db.record_run(started_at, utc_now_iso(), "locked", {}, errors, [], job_type="retry_failed", effective_config=effective_config)
        return JobResult(job_type="retry_failed", status="locked", errors=errors)

    counts: dict[str, int] = {}
    errors: list[str] = []
    outputs: list[str] = []
    retry_sources: set[str] = set()
    new_items = []
    try:
        latest_daily = db.latest_run("daily")
        if latest_daily is None:
            errors.append("no daily run found")
        else:
            retry_sources = {
                source
                for source, status in db.source_runs_for_run(latest_daily["run_id"]).items()
                if status["retry_eligible"]
            }
        if retry_sources:
            deadline = time.monotonic() + (float(effective_config["budget_minutes"]) * 60)
            raw_store = RawStore(root)
            items, counts, errors = collect_all(
                root,
                raw_store,
                app_config.sources,
                started_at,
                live_network=True,
                only_sources=retry_sources,
                deadline=deadline,
            )
            seen = db.item_ids()
            new_items = [item for item in _dedupe_items(items) if item.item_id not in seen]
            db.upsert_items(new_items)
            if effective_config.get("update_daily_digest", True):
                output = _append_retry_summary(root, started_at[:10], retry_sources, counts, errors)
                outputs.append(str(output))

        status = _job_status(new_items, errors)
        run_id = db.record_run(
            started_at,
            utc_now_iso(),
            status,
            counts,
            errors,
            outputs,
            job_type="retry_failed",
            effective_config=effective_config,
        )
        for source, source_status in _source_statuses(app_config.sources, counts, errors, retry_sources).items():
            db.record_source_run(
                run_id,
                source,
                source_status["status"],
                source_status["count"],
                source_status["error"],
                source_status["retry_eligible"],
            )
        return JobResult(
            job_type="retry_failed",
            status=status,
            counts=counts,
            errors=errors,
            outputs=outputs,
            item_count=len(new_items),
        )
    finally:
        db.release_lock("pipeline")


def run_enrich(
    root: Path,
    now: str | None = None,
    since: str | None = None,
    budget_minutes: int | None = None,
    top_n: int | None = None,
) -> JobResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    app_config = load_app_config(root / "config" / "sources.yaml", root / "config" / "topics.yaml")
    jobs_config = load_jobs_config(root / "config" / "jobs.yaml")
    effective_config = effective_job_config(
        jobs_config,
        "enrich",
        {"since": since, "budget_minutes": budget_minutes, "top_n": top_n},
    )
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()

    if not db.acquire_lock("enrich", "enrich", started_at, int(effective_config.get("budget_minutes", 60))):
        errors = ["active lock prevents enrich run"]
        db.record_run(started_at, utc_now_iso(), "locked", {}, errors, [], job_type="enrich", effective_config=effective_config)
        return JobResult(job_type="enrich", status="locked", errors=errors)

    outputs: list[str] = []
    errors: list[str] = []
    try:
        ranked = rank_items(
            db.list_items(),
            app_config.topics,
            now=started_at,
            limit=int(effective_config["top_n"]),
            seen_item_ids=set(),
        )
        for entry in ranked:
            output = _upsert_wiki_evidence(root, entry.item, started_at[:10])
            if output is not None:
                outputs.append(str(output))
        status = "ok" if outputs or not ranked else "ok"
        db.record_run(
            started_at,
            utc_now_iso(),
            status,
            {"updated_pages": len(outputs)},
            errors,
            outputs,
            job_type="enrich",
            effective_config=effective_config,
        )
        return JobResult(job_type="enrich", status=status, counts={"updated_pages": len(outputs)}, outputs=outputs)
    finally:
        db.release_lock("enrich")


def run_health(root: Path, now: str | None = None, cleanup_stale_locks: bool = False) -> HealthResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    jobs_config = load_jobs_config(root / "config" / "jobs.yaml")
    effective_config = effective_job_config(jobs_config, "maintenance", {})
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()

    issues: list[str] = []
    cleaned: list[str] = []
    lint = lint_wiki(root)
    if not lint.ok:
        issues.extend(f"wiki lint: {error}" for error in lint.errors)
    integrity = db.integrity_check()
    if integrity != "ok":
        issues.append(f"sqlite integrity: {integrity}")
    duplicates = db.duplicate_candidates()
    if duplicates:
        issues.extend(f"duplicate item url: {entry['url']} ({entry['count']})" for entry in duplicates)
    active_locks = db.active_locks()
    stale_threshold = int(effective_config.get("stale_lock_after_minutes", 120))
    stale = [lock for lock in active_locks if _lock_is_stale(lock["acquired_at"], started_at, stale_threshold)]
    if stale:
        issues.extend(f"stale lock: {lock['name']} held by {lock['job_type']}" for lock in stale)
        if cleanup_stale_locks:
            cleaned = db.cleanup_stale_locks(started_at, stale_threshold)
    status = "ok" if not issues else "error"
    db.record_run(
        started_at,
        utc_now_iso(),
        status,
        {"issues": len(issues), "cleaned_locks": len(cleaned)},
        issues,
        [],
        job_type="health",
        effective_config=effective_config,
    )
    return HealthResult(status=status, issues=issues, cleaned_locks=cleaned)


def run_state_vacuum(root: Path, now: str | None = None) -> VacuumResult:
    root = Path(root).resolve()
    started_at = now or utc_now_iso()
    jobs_config = load_jobs_config(root / "config" / "jobs.yaml")
    effective_config = effective_job_config(jobs_config, "maintenance", {})
    db = Database(root / "state" / "frontier-radar.sqlite")
    db.init()
    cleaned = db.cleanup_stale_locks(started_at, int(effective_config.get("stale_lock_after_minutes", 120)))
    db.vacuum()
    db.record_run(
        started_at,
        utc_now_iso(),
        "ok",
        {"cleaned_locks": len(cleaned)},
        [],
        [],
        job_type="state_vacuum",
        effective_config=effective_config,
    )
    return VacuumResult(status="ok", cleaned_locks=cleaned)


def _append_retry_summary(
    root: Path,
    date: str,
    retry_sources: set[str],
    counts: dict[str, int],
    errors: list[str],
) -> Path:
    relative = Path("wiki") / "daily" / f"{date}.md"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["", "## Retry Update", ""]
    lines.append(f"- Retried sources: {', '.join(sorted(retry_sources)) or 'none'}")
    for source, count in sorted(counts.items()):
        lines.append(f"- {source}: recovered {count} item(s)")
    for error in errors:
        lines.append(f"- Error: {error}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    return relative


def _upsert_wiki_evidence(root: Path, item, date: str) -> Path | None:
    page = _wiki_page_for_item(item)
    path = root / page
    path.parent.mkdir(parents=True, exist_ok=True)
    title = _clean_inline(item.title)
    evidence = f"- {date}: [{title}]({item.url}) (raw: `{item.raw_path}`)"
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = f"# {title}\n\n## Evidence\n"
    if evidence in text:
        return None
    if "## Evidence" not in text:
        text = text.rstrip() + "\n\n## Evidence\n"
    text = text.rstrip() + "\n" + evidence + "\n"
    path.write_text(text, encoding="utf-8")
    return page


def _wiki_page_for_item(item) -> Path:
    slug = _slug(item.title)
    if item.source_type == "repo":
        return Path("wiki/repos") / f"{slug}.md"
    if item.source_type == "paper":
        return Path("wiki/papers") / f"{slug}.md"
    if item.source_type == "expert-note":
        return Path("wiki/claims") / f"{slug}.md"
    return Path("wiki/topics") / f"{slug}.md"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _clean_inline(value).casefold()).strip("-")
    return slug[:80] or "untitled"


def _clean_inline(value: str) -> str:
    return " ".join(str(value).split()).replace("[", r"\[").replace("]", r"\]")


def _job_status(items: list[Any], errors: list[str]) -> str:
    if not errors:
        return "ok"
    if items:
        return "partial"
    return "error"


def _lock_is_stale(acquired_at: str, now: str, stale_after_minutes: int) -> bool:
    age = _parse_time(now) - _parse_time(acquired_at)
    return age.total_seconds() >= stale_after_minutes * 60


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
