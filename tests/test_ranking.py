from frontier_radar.models import NormalizedItem
from frontier_radar.ranking import rank_items, score_item


def item(
    title,
    summary,
    metrics,
    published_at="2026-06-22T15:00:00+00:00",
    url=None,
):
    return NormalizedItem(
        source="github",
        source_type="repo",
        title=title,
        url=url or f"https://example.com/{title.replace(' ', '-')}",
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
    assert scored.components["novelty"] == 1.0
    assert scored.components["source_weight"] > 0.0
    assert scored.score > 4.0


def test_score_item_marks_seen_items_as_not_novel():
    topics = {"topics": {"agents": {"keywords": ["agent"]}}}
    new_item = item("Agent Runtime", "Agent notes", {"stars": 1})

    scored = score_item(
        new_item,
        topics,
        now="2026-06-22T16:00:00+00:00",
        seen_item_ids={new_item.item_id},
    )

    assert scored.components["novelty"] == 0.0


def test_score_item_handles_invalid_item_timestamp_without_crashing():
    topics = {"topics": {"agents": {"keywords": ["agent"]}}}

    scored = score_item(
        item("Agent Runtime", "Agent notes", {"stars": 1}, published_at="not-a-date"),
        topics,
        now="2026-06-22T16:00:00+00:00",
    )

    assert scored.components["freshness"] == 0.0


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


def test_rank_items_applies_configured_component_weights_for_calibration():
    topics = {
        "ranking_weights": {
            "momentum": 0.2,
            "relevance": 3.0,
        },
        "topics": {"agents": {"keywords": ["agent", "tool use"]}},
    }
    ranked = rank_items(
        [
            item("Mega Database", "Storage engine notes", {"stars": 100_000}),
            item("Focused Agent Tooling", "Agent tool use workflow", {"stars": 1}),
        ],
        topics,
        now="2026-06-22T16:00:00+00:00",
    )

    assert ranked[0].item.title == "Focused Agent Tooling"


def test_rank_items_uses_url_tiebreaker_for_equal_scores_and_titles():
    topics = {"topics": {"agents": {"keywords": ["agent"]}}}
    ranked = rank_items(
        [
            item(
                "Agent Notes",
                "AI agent framework",
                {"stars": 100},
                url="https://example.com/z",
            ),
            item(
                "Agent Notes",
                "AI agent framework",
                {"stars": 100},
                url="https://example.com/a",
            ),
        ],
        topics,
        now="2026-06-22T16:00:00+00:00",
    )

    assert ranked[0].item.url == "https://example.com/a"
