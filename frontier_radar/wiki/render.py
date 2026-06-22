from __future__ import annotations

from datetime import date as calendar_date
from pathlib import Path
import re

from frontier_radar.ranking import RankedItem


DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def render_daily_digest(
    date: str,
    ranked_items: list[RankedItem],
    counts: dict[str, int],
    errors: list[str],
) -> str:
    lines = [
        f"# Frontier Radar Daily - {date}",
        "",
        "## Executive Summary",
        "",
    ]
    if ranked_items:
        for entry in ranked_items[:10]:
            title = _markdown_link_text(entry.item.title)
            source = _inline_text(entry.item.source)
            raw_path = _inline_text(entry.item.raw_path)
            lines.append(
                f"- [{title}]({entry.item.url}) from {source} "
                f"(score {entry.score:.2f}; raw: `{raw_path}`)"
            )
    else:
        lines.append("- No items collected.")

    lines.extend(["", "## Top Items", ""])
    for entry in ranked_items:
        title = _inline_text(entry.item.title)
        link_title = _markdown_link_text(entry.item.title)
        source = _inline_text(entry.item.source)
        source_type = _inline_text(entry.item.source_type)
        author = _inline_text(entry.item.author)
        published_at = _inline_text(entry.item.published_at)
        raw_path = _inline_text(entry.item.raw_path)
        summary = _inline_text(entry.item.summary)
        components = ", ".join(
            f"{key}={value:.2f}" for key, value in sorted(entry.components.items())
        )
        lines.extend(
            [
                f"### {title}",
                "",
                f"- Source: `{source}` / `{source_type}`",
                f"- URL: [{link_title}]({entry.item.url}) (raw: `{raw_path}`)",
                f"- Author: {author}",
                f"- Published: {published_at}",
                f"- Score: {entry.score:.2f} ({components})",
                f"- Provenance: `{raw_path}`",
                f"- Summary: {summary}",
                "",
            ]
        )

    lines.extend(["## Run Metadata", ""])
    for source, count in sorted(counts.items()):
        lines.append(f"- {source}: {count} items")
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors:
            lines.append(f"- {_error_text(error)}")
    return "\n".join(lines).rstrip() + "\n"


def write_daily_digest(
    root: Path,
    date: str,
    ranked_items: list[RankedItem],
    counts: dict[str, int],
    errors: list[str],
) -> Path:
    _validate_date(date)
    relative = Path("wiki") / "daily" / f"{date}.md"
    absolute = root / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(
        render_daily_digest(date, ranked_items, counts, errors),
        encoding="utf-8",
    )
    return relative


def _validate_date(value: str) -> None:
    if not DATE_PATTERN.fullmatch(value):
        raise ValueError(f"date must be YYYY-MM-DD: {value!r}")
    try:
        calendar_date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD: {value!r}") from exc


def _inline_text(value: str) -> str:
    return " ".join(str(value).split())


def _markdown_link_text(value: str) -> str:
    return _inline_text(value).replace("[", r"\[").replace("]", r"\]")


def _error_text(value: str) -> str:
    return _inline_text(value).replace("https://", "hxxps://").replace("http://", "hxxp://")
