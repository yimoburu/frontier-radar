from frontier_radar.storage import Database


def test_database_records_effective_config_and_source_runs(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()

    run_id = db.record_run(
        started_at="2026-06-22T15:00:00+00:00",
        finished_at="2026-06-22T15:01:00+00:00",
        status="partial",
        counts={"github": 1},
        errors=["rss: timeout"],
        outputs=["wiki/daily/2026-06-22.md"],
        job_type="daily",
        effective_config={"budget_minutes": 20, "top_n": 30},
    )
    db.record_source_run(
        run_id=run_id,
        source="rss",
        status="timeout",
        count=0,
        error="timeout",
        retry_eligible=True,
    )

    latest = db.latest_run("daily")
    source_runs = db.source_runs_for_run(run_id)

    assert latest["effective_config"]["budget_minutes"] == 20
    assert latest["job_type"] == "daily"
    assert source_runs["rss"]["status"] == "timeout"
    assert source_runs["rss"]["retry_eligible"] is True


def test_database_lock_blocks_until_stale_threshold(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()

    acquired = db.acquire_lock(
        name="pipeline",
        job_type="daily",
        acquired_at="2026-06-22T15:00:00+00:00",
        stale_after_minutes=60,
    )
    blocked = db.acquire_lock(
        name="pipeline",
        job_type="retry_failed",
        acquired_at="2026-06-22T15:10:00+00:00",
        stale_after_minutes=60,
    )
    reclaimed = db.acquire_lock(
        name="pipeline",
        job_type="retry_failed",
        acquired_at="2026-06-22T17:00:00+00:00",
        stale_after_minutes=60,
    )

    assert acquired is True
    assert blocked is False
    assert reclaimed is True
    assert db.active_locks()[0]["job_type"] == "retry_failed"


def test_database_vacuum_and_duplicate_health_helpers(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    db.init()

    assert db.integrity_check() == "ok"
    assert db.vacuum() is None
