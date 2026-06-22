from __future__ import annotations

from datetime import date as calendar_date
from pathlib import Path

from frontier_radar.models import NormalizedItem


def collect_manual_notes(
    root: Path,
    directory: str,
    errors: list[str] | None = None,
) -> list[NormalizedItem]:
    root = root.resolve()
    base = (root / directory).resolve()
    if base != root and root not in base.parents:
        raise ValueError(f"unsafe manual notes directory: {directory!r}")
    if not base.exists():
        return []
    items: list[NormalizedItem] = []
    for path in sorted(base.glob("*.md")):
        resolved_path = path.resolve()
        if resolved_path != base and base not in resolved_path.parents:
            continue
        relative_path = path.relative_to(root)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.startswith("- "):
                continue
            parts = [part.strip() for part in line[2:].split("|", maxsplit=3)]
            if len(parts) != 4:
                continue
            date, author, url, summary = parts
            try:
                calendar_date.fromisoformat(date)
            except ValueError:
                if errors is not None:
                    errors.append(f"manual note {relative_path}:{line_number}: invalid date {date!r}")
                continue
            items.append(
                NormalizedItem(
                    source="manual",
                    source_type="expert-note",
                    title=summary[:80],
                    url=url,
                    author=author,
                    published_at=f"{date}T00:00:00+00:00",
                    summary=summary,
                    raw_path=str(relative_path),
                    tags=["manual", "x-adjacent"],
                    metrics={},
                    metadata={"note_file": str(relative_path)},
                )
            )
    return items
