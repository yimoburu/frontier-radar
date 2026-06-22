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
            url = _markdown_url(entry.item.url)
            source = _inline_text(entry.item.source)
            raw_path = _inline_text(entry.item.raw_path)
            lines.append(
                f"- [{title}]({url}) from {source} "
                f"(score {entry.score:.2f}; raw: `{raw_path}`)"
            )
    else:
        lines.append("- No items collected.")

    lines.extend(["", "## Top Repositories", ""])
    lines.extend(_compact_item_lines(_filter_items(ranked_items, source_type="repo")))

    lines.extend(["", "## Top Papers", ""])
    lines.extend(_compact_item_lines(_filter_items(ranked_items, source_type="paper")))

    lines.extend(["", "## Top Discussions", ""])
    lines.extend(_compact_item_lines(_filter_items(ranked_items, source_type="discussion")))

    lines.extend(["", "## Top Videos Or Talks", ""])
    lines.extend(_compact_item_lines(_video_items(ranked_items)))

    lines.extend(["", "## Emerging Topics", ""])
    lines.extend(_emerging_topic_lines(ranked_items))

    lines.extend(["", "## Claims To Revisit", ""])
    lines.extend(_claims_to_revisit_lines(ranked_items))

    lines.extend(["", "## Suggested Wiki Pages", ""])
    lines.extend(_suggested_page_lines(ranked_items))

    lines.extend(["", "## Top Items", ""])
    for entry in ranked_items:
        title = _inline_text(entry.item.title)
        link_title = _markdown_link_text(entry.item.title)
        url = _markdown_url(entry.item.url)
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
                f"- URL: [{link_title}]({url}) (raw: `{raw_path}`)",
                f"- Author: {author}",
                f"- Published: {published_at}",
                f"- Score: {entry.score:.2f} ({components})",
                f"- Provenance: `{raw_path}`",
                f"- Summary: {summary} (raw: `{raw_path}`)",
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


def _markdown_url(value: str) -> str:
    return _inline_text(value).replace("(", "%28").replace(")", "%29")


def _error_text(value: str) -> str:
    return _inline_text(value).replace("https://", "hxxps://").replace("http://", "hxxp://")


def _filter_items(
    ranked_items: list[RankedItem],
    source_type: str,
    limit: int = 5,
) -> list[RankedItem]:
    return [entry for entry in ranked_items if entry.item.source_type == source_type][:limit]


def _video_items(ranked_items: list[RankedItem], limit: int = 5) -> list[RankedItem]:
    return [
        entry
        for entry in ranked_items
        if entry.item.source == "youtube"
        or "video" in entry.item.source_type.casefold()
        or "talk" in " ".join(entry.item.tags).casefold()
    ][:limit]


def _compact_item_lines(entries: list[RankedItem]) -> list[str]:
    if not entries:
        return ["- None captured in this run."]
    lines: list[str] = []
    for entry in entries:
        title = _markdown_link_text(entry.item.title)
        url = _markdown_url(entry.item.url)
        raw_path = _inline_text(entry.item.raw_path)
        lines.append(f"- [{title}]({url}) (score {entry.score:.2f}; raw: `{raw_path}`)")
    return lines


def _emerging_topic_lines(ranked_items: list[RankedItem]) -> list[str]:
    counts: dict[str, int] = {}
    for entry in ranked_items:
        for tag in entry.item.tags:
            label = _inline_text(tag)
            if label:
                counts[label] = counts.get(label, 0) + 1
    if not counts:
        return ["- None detected yet."]
    return [f"- {topic}: {count} item(s)" for topic, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]]


def _claims_to_revisit_lines(ranked_items: list[RankedItem]) -> list[str]:
    claim_like = [
        entry
        for entry in ranked_items
        if entry.item.source_type in {"expert-note", "paper", "feed"}
        and any(word in entry.item.summary.casefold() for word in ["claim", "benchmark", "sota", "state-of-the-art", "outperform"])
    ][:5]
    if not claim_like:
        return ["- None flagged by the current heuristic."]
    return _compact_item_lines(claim_like)


def _suggested_page_lines(ranked_items: list[RankedItem]) -> list[str]:
    if not ranked_items:
        return ["- None."]
    lines: list[str] = []
    for entry in ranked_items[:10]:
        page = _suggested_page(entry)
        title = _markdown_link_text(entry.item.title)
        url = _markdown_url(entry.item.url)
        raw_path = _inline_text(entry.item.raw_path)
        lines.append(f"- `{page}` from [{title}]({url}) (raw: `{raw_path}`)")
    return lines


def _suggested_page(entry: RankedItem) -> str:
    title = _slug(entry.item.title)
    if entry.item.source_type == "repo":
        return f"wiki/repos/{title}.md"
    if entry.item.source_type == "paper":
        return f"wiki/papers/{title}.md"
    if entry.item.source_type == "expert-note":
        return f"wiki/claims/{title}.md"
    return f"wiki/topics/{title}.md"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _inline_text(value).casefold()).strip("-")
    return slug[:80] or "untitled"
