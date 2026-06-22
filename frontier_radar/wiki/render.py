from __future__ import annotations

from pathlib import Path

from frontier_radar.ranking import RankedItem


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
            lines.append(
                f"- [{entry.item.title}]({entry.item.url}) from {entry.item.source} "
                f"(score {entry.score:.2f}; raw: `{entry.item.raw_path}`)"
            )
    else:
        lines.append("- No items collected.")

    lines.extend(["", "## Top Items", ""])
    for entry in ranked_items:
        components = ", ".join(
            f"{key}={value:.2f}" for key, value in sorted(entry.components.items())
        )
        lines.extend(
            [
                f"### {entry.item.title}",
                "",
                f"- Source: `{entry.item.source}` / `{entry.item.source_type}`",
                f"- URL: {entry.item.url}",
                f"- Author: {entry.item.author}",
                f"- Published: {entry.item.published_at}",
                f"- Score: {entry.score:.2f} ({components})",
                f"- Provenance: `{entry.item.raw_path}`",
                f"- Summary: {entry.item.summary}",
                "",
            ]
        )

    lines.extend(["## Run Metadata", ""])
    for source, count in sorted(counts.items()):
        lines.append(f"- {source}: {count} items")
    if errors:
        lines.extend(["", "## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
    return "\n".join(lines).rstrip() + "\n"


def write_daily_digest(
    root: Path,
    date: str,
    ranked_items: list[RankedItem],
    counts: dict[str, int],
    errors: list[str],
) -> Path:
    relative = Path("wiki") / "daily" / f"{date}.md"
    absolute = root / relative
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(
        render_daily_digest(date, ranked_items, counts, errors),
        encoding="utf-8",
    )
    return relative
