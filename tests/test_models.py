from frontier_radar.models import NormalizedItem, ScoredItem


def test_normalized_item_derives_stable_id_from_url():
    item = NormalizedItem(
        source="github",
        source_type="repo",
        title="Example Repo",
        url="https://github.com/example/repo",
        author="example",
        published_at="2026-06-22T08:00:00+00:00",
        summary="An example item.",
        raw_path="raw/2026-06-22/github/example.json",
        tags=["agents"],
        metrics={"stars": 123},
        metadata={"language": "Python"},
    )

    assert item.item_id == "ffc8e3beb425"
    assert item.to_record()["metrics"]["stars"] == 123


def test_scored_item_orders_by_score_descending():
    low = ScoredItem(item_id="low", score=1.0, components={"freshness": 1.0})
    high = ScoredItem(item_id="high", score=3.0, components={"freshness": 1.0})

    assert sorted([low, high], reverse=True)[0].item_id == "high"
