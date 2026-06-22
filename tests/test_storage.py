from frontier_radar.models import NormalizedItem
from frontier_radar.storage import Database


def make_item(url="https://example.com/a"):
    return NormalizedItem(
        source="hn",
        source_type="discussion",
        title="AI agents discussion",
        url=url,
        author="alice",
        published_at="2026-06-22T15:00:00+00:00",
        summary="A useful discussion.",
        raw_path="raw/2026-06-22/hn/a.json",
        tags=["agents"],
        metrics={"points": 42},
        metadata={},
    )


def test_database_upserts_and_lists_items(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()
    db.upsert_items([make_item()])
    db.upsert_items([make_item()])

    items = db.list_items()

    assert len(items) == 1
    assert items[0].title == "AI agents discussion"
    assert items[0].metrics["points"] == 42
    assert db.item_ids() == {make_item().item_id}


def test_database_records_run_metadata(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()

    run_id = db.record_run(
        started_at="2026-06-22T15:00:00+00:00",
        finished_at="2026-06-22T15:01:00+00:00",
        status="ok",
        counts={"hn": 1},
        errors=[],
        outputs=["wiki/daily/2026-06-22.md"],
    )

    assert run_id == 1
    assert db.latest_run()["status"] == "ok"
