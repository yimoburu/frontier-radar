from pathlib import Path

from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import RankedItem
from frontier_radar.wiki.render import render_daily_digest, write_daily_digest


def ranked_item():
    item = NormalizedItem(
        source="github",
        source_type="repo",
        title="Agent Framework",
        url="https://github.com/example/agent-framework",
        author="example",
        published_at="2026-06-22T15:00:00+00:00",
        summary="A useful AI agent framework.",
        raw_path="raw/2026-06-22/github/item.json",
        tags=["agents"],
        metrics={"stars": 500},
        metadata={},
    )
    return RankedItem(
        item=item,
        score=5.5,
        components={"freshness": 1.0, "momentum": 2.5, "relevance": 2.0},
    )


def test_render_daily_digest_includes_provenance_and_scores():
    markdown = render_daily_digest(
        date="2026-06-22",
        ranked_items=[ranked_item()],
        counts={"github": 1},
        errors=[],
    )

    assert "# Frontier Radar Daily - 2026-06-22" in markdown
    assert "Agent Framework" in markdown
    assert "raw/2026-06-22/github/item.json" in markdown
    assert "score 5.50" in markdown


def test_write_daily_digest_creates_expected_path(tmp_path):
    path = write_daily_digest(
        tmp_path,
        "2026-06-22",
        [ranked_item()],
        {"github": 1},
        [],
    )

    assert path == Path("wiki/daily/2026-06-22.md")
    assert (tmp_path / path).exists()
