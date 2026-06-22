from pathlib import Path

import pytest

from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import RankedItem
from frontier_radar.wiki.render import render_daily_digest, write_daily_digest


def ranked_item(
    title="Agent Framework",
    summary="A useful AI agent framework.",
    url="https://github.com/example/agent-framework",
):
    item = NormalizedItem(
        source="github",
        source_type="repo",
        title=title,
        url=url,
        author="example",
        published_at="2026-06-22T15:00:00+00:00",
        summary=summary,
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
    assert "## Top Repositories" in markdown
    assert "## Top Papers" in markdown
    assert "## Top Discussions" in markdown
    assert "## Top Videos Or Talks" in markdown
    assert "## Emerging Topics" in markdown
    assert "## Claims To Revisit" in markdown
    assert "## Suggested Wiki Pages" in markdown


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


@pytest.mark.parametrize("date", ["../../escape", "2026-6-22", "2026-06-22.md"])
def test_write_daily_digest_rejects_invalid_dates(tmp_path, date):
    with pytest.raises(ValueError):
        write_daily_digest(tmp_path, date, [ranked_item()], {"github": 1}, [])


def test_render_daily_digest_normalizes_markdown_fields():
    markdown = render_daily_digest(
        date="2026-06-22",
        ranked_items=[
            ranked_item(
                title="Agent ](Injected)\n- injected title bullet",
                summary="Useful summary.\n- injected summary bullet",
            )
        ],
        counts={"github": 1},
        errors=[],
    )

    assert "Agent \\](Injected) - injected title bullet" in markdown
    assert "Useful summary. - injected summary bullet" in markdown
    assert "\n- injected title bullet" not in markdown
    assert "\n- injected summary bullet" not in markdown
