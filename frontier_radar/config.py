from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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
