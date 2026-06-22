from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import rank_items, score_item


def item(title, summary, metrics, published_at="2026-06-22T15:00:00+00:00"):
    return NormalizedItem(
        source="github",
        source_type="repo",
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        author="owner",
        published_at=published_at,
        summary=summary,
        raw_path="raw/2026-06-22/github/item.json",
        tags=[],
        metrics=metrics,
        metadata={},
    )


def test_score_item_combines_freshness_momentum_and_relevance():
    topics = {"topics": {"agents": {"keywords": ["agent", "tool use"]}}}
    scored = score_item(
        item("Agent Runtime", "Tool use for coding agents", {"stars": 250}),
        topics,
        now="2026-06-22T16:00:00+00:00",
    )

    assert scored.components["freshness"] > 0.9
    assert scored.components["momentum"] > 0.0
    assert scored.components["relevance"] == 2.0
    assert scored.score > 3.0


def test_rank_items_returns_highest_scores_first():
    topics = {"topics": {"agents": {"keywords": ["agent"]}}}
    ranked = rank_items(
        [
            item("Unrelated", "Database notes", {"stars": 5}),
            item("Agent Framework", "AI agent framework", {"stars": 500}),
        ],
        topics,
        now="2026-06-22T16:00:00+00:00",
        limit=1,
    )

    assert ranked[0].item.title == "Agent Framework"
