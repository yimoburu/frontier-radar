from __future__ import annotations

from pathlib import Path

from frontier_radar.models import NormalizedItem


def collect_manual_notes(root: Path, directory: str) -> list[NormalizedItem]:
    root = root.resolve()
    base = (root / directory).resolve()
    if base != root and root not in base.parents:
        raise ValueError(f"unsafe manual notes directory: {directory!r}")
    if not base.exists():
        return []
    items: list[NormalizedItem] = []
    for path in sorted(base.glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("- "):
                continue
            parts = [part.strip() for part in line[2:].split("|", maxsplit=3)]
            if len(parts) != 4:
                continue
            date, author, url, summary = parts
            items.append(
                NormalizedItem(
                    source="manual",
                    source_type="expert-note",
                    title=summary[:80],
                    url=url,
                    author=author,
                    published_at=f"{date}T00:00:00+00:00",
                    summary=summary,
                    raw_path=str(path.relative_to(root)),
                    tags=["manual", "x-adjacent"],
                    metrics={},
                    metadata={"note_file": str(path.relative_to(root))},
                )
            )
    return items
