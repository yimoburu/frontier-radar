from pathlib import Path

import pytest

from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import RankedItem
from frontier_radar.wiki.render import render_daily_digest, write_daily_digest


def ranked_item(
    title="Agent Framework",
    summary="A useful AI agent framework.",
    url="https://github.com/example/agent-framework",
    source="github",
    source_type="repo",
    raw_path="raw/2026-06-22/github/item.json",
    tags=None,
    score=5.5,
    components=None,
):
    item = NormalizedItem(
        source=source,
        source_type=source_type,
        title=title,
        url=url,
        author="example",
        published_at="2026-06-22T15:00:00+00:00",
        summary=summary,
        raw_path=raw_path,
        tags=tags or ["agents"],
        metrics={"stars": 500},
        metadata={},
    )
    return RankedItem(
        item=item,
        score=score,
        components=components or {"freshness": 1.0, "momentum": 2.5, "relevance": 2.0},
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


def test_render_daily_digest_synthesizes_patterns_and_followups():
    markdown = render_daily_digest(
        date="2026-06-22",
        ranked_items=[
            ranked_item(
                title="Agent Memory Bench",
                summary="Benchmark claim for agent memory tools.",
                url="https://arxiv.org/abs/2606.00001",
                source="arxiv",
                source_type="paper",
                raw_path="raw/2026-06-22/arxiv/agent-memory.json",
                tags=["agents", "memory"],
                score=7.0,
            ),
            ranked_item(
                title="agent-memory-lab",
                summary="Open source agent memory evaluation harness.",
                raw_path="raw/2026-06-22/github/agent-memory-lab.json",
                tags=["agents", "memory"],
                score=6.2,
            ),
            ranked_item(
                title="Production Agents Talk",
                summary="Talk about operating agent systems.",
                url="https://youtube.example/watch?v=agent",
                source="youtube",
                source_type="video",
                raw_path="raw/2026-06-22/youtube/agent-talk.json",
                tags=["agents"],
                score=4.8,
            ),
        ],
        counts={"arxiv": 1, "github": 1, "youtube": 1},
        errors=[],
    )

    assert "## Intelligence Brief" in markdown
    assert "- Lead signal: Agent Memory Bench" in markdown
    assert "- Pattern: `agents` appears in 3 item(s) across arxiv, github, youtube" in markdown
    assert "- Follow-up: update `wiki/topics/agents.md`" in markdown
    assert "Provenance: `raw/2026-06-22/arxiv/agent-memory.json`" in markdown
