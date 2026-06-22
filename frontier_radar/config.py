from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_JOBS_CONFIG: dict[str, dict[str, Any]] = {
    "daily": {
        "budget_minutes": 20,
        "top_n": 30,
        "max_deep_reads": 15,
        "partial_digest": True,
        "prevent_overlapping_runs": True,
        "stale_run_after_minutes": 60,
        "terminal_summary_items": 5,
    },
    "retry_failed": {
        "enabled": True,
        "budget_minutes": 10,
        "retry_window": "today",
        "max_attempts_per_source": 2,
        "update_daily_digest": True,
    },
    "enrich": {
        "enabled": True,
        "budget_minutes": 60,
        "since": "7d",
        "top_n": 100,
        "update_topic_pages": True,
        "update_entity_pages": True,
        "update_claim_pages": True,
        "require_provenance_links": True,
    },
    "maintenance": {
        "enabled": True,
        "lint_wiki": True,
        "check_provenance": True,
        "check_broken_links": True,
        "check_duplicate_items": True,
        "vacuum_state": True,
        "stale_lock_after_minutes": 120,
    },
}


@dataclass(frozen=True)
class AppConfig:
    sources: dict[str, Any]
    topics: dict[str, Any]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_root() / path
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {resolved}")
    return data


def load_app_config(
    sources_path: Path | str = Path("config/sources.yaml"),
    topics_path: Path | str = Path("config/topics.yaml"),
) -> AppConfig:
    return AppConfig(
        sources=load_yaml(Path(sources_path)),
        topics=load_yaml(Path(topics_path)),
    )


def load_jobs_config(path: Path | str | None = Path("config/jobs.yaml")) -> dict[str, dict[str, Any]]:
    config = _deep_copy(DEFAULT_JOBS_CONFIG)
    if path is None:
        return config
    resolved = Path(path)
    if not resolved.exists() and not resolved.is_absolute():
        resolved = repo_root() / resolved
    if not resolved.exists():
        return config
    overrides = load_yaml(resolved)
    for job, values in overrides.items():
        if not isinstance(values, dict):
            raise ValueError(f"Expected mapping for job config {job!r}")
        base = config.setdefault(str(job), {})
        base.update(values)
    return config


def effective_job_config(
    jobs_config: dict[str, dict[str, Any]],
    job_type: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if job_type not in jobs_config:
        raise ValueError(f"unknown job type: {job_type}")
    effective = dict(jobs_config[job_type])
    for key, value in (overrides or {}).items():
        if value is not None:
            effective[key] = value
    return effective


def _deep_copy(value: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {key: dict(inner) for key, inner in value.items()}
