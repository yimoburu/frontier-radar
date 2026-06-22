from pathlib import Path

from frontier_radar.daily import run_daily
from frontier_radar.jobs import run_enrich, run_health, run_retry_failed, run_state_vacuum
from frontier_radar.models import NormalizedItem
from frontier_radar.storage import Database


def write_config(root, sources_text, jobs_text=""):
    (root / "config").mkdir()
    (root / "config" / "sources.yaml").write_text(sources_text, encoding="utf-8")
    (root / "config" / "topics.yaml").write_text(
        "topics:\n  agents:\n    keywords: ['agent']\n",
        encoding="utf-8",
    )
    if jobs_text:
        (root / "config" / "jobs.yaml").write_text(jobs_text, encoding="utf-8")


def make_item(url="https://example.com/agent", raw_path="raw/2026-06-22/github/item.json"):
    return NormalizedItem(
        source="github",
        source_type="repo",
        title="example/agent",
        url=url,
        author="example",
        published_at="2026-06-22T15:00:00+00:00",
        summary="agent framework",
        raw_path=raw_path,
        tags=["Python"],
        metrics={"stars": 10},
        metadata={},
    )


def test_daily_records_partial_source_status_and_effective_config(tmp_path):
    write_config(
        tmp_path,
        "manual:\n  enabled: true\n  directory: manual\n",
        "daily:\n  budget_minutes: 9\n  top_n: 1\n",
    )
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "x-notes.md").write_text(
        "- bad-date | Expert | https://x.com/example/bad | bad agent note\n"
        "- 2026-06-22 | Expert | https://x.com/example/good | good agent note\n",
        encoding="utf-8",
    )

    result = run_daily(
        tmp_path,
        now="2026-06-22T15:00:00+00:00",
        live_network=False,
        budget_minutes=3,
        top_n=1,
    )
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    latest = db.latest_run("daily")
    source_runs = db.source_runs_for_run(latest["run_id"])

    assert result.status == "partial"
    assert latest["effective_config"]["budget_minutes"] == 3
    assert latest["effective_config"]["top_n"] == 1
    assert source_runs["manual"]["status"] == "partial"
    assert source_runs["manual"]["retry_eligible"] is True


def test_daily_saves_raw_snapshot_before_ranking_failure(tmp_path, monkeypatch):
    write_config(tmp_path, "github:\n  enabled: true\n  queries: ['agent']\n")

    def fake_collect_github(config, raw_store, now, errors=None):
        raw_path = raw_store.write_snapshot("github", "json", b'{"items":[]}', now=now)
        return [make_item(raw_path=str(raw_path))]

    def fail_rank(*args, **kwargs):
        raise RuntimeError("rank failed")

    monkeypatch.setattr("frontier_radar.daily.collect_github", fake_collect_github)
    monkeypatch.setattr("frontier_radar.daily.rank_items", fail_rank)

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00")

    assert result.status == "error"
    assert (tmp_path / "raw/2026-06-22/github/20260622T150000Z.json").exists()
    assert "rank failed" in (tmp_path / result.digest_path).read_text(encoding="utf-8")


def test_daily_exits_cleanly_when_pipeline_lock_exists(tmp_path):
    write_config(tmp_path, "manual:\n  enabled: false\n")
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    db.acquire_lock(
        name="pipeline",
        job_type="retry_failed",
        acquired_at="2026-06-22T15:00:00+00:00",
        stale_after_minutes=60,
    )

    result = run_daily(tmp_path, now="2026-06-22T15:10:00+00:00", live_network=False)

    assert result.status == "locked"
    assert "active lock" in result.errors[0]
    assert db.latest_run("daily")["status"] == "locked"


def test_retry_failed_only_retries_retry_eligible_sources(tmp_path, monkeypatch):
    write_config(
        tmp_path,
        "github:\n  enabled: true\n  queries: ['agent']\n"
        "rss:\n  enabled: true\n  feeds:\n"
        "    - name: Example\n      url: https://example.com/feed.xml\n",
    )
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    run_id = db.record_run(
        "2026-06-22T15:00:00+00:00",
        "2026-06-22T15:01:00+00:00",
        "partial",
        {"github": 1, "rss": 0},
        ["rss: timeout"],
        ["wiki/daily/2026-06-22.md"],
        job_type="daily",
        effective_config={},
    )
    db.record_source_run(run_id, "github", "success", 1, "", False)
    db.record_source_run(run_id, "rss", "timeout", 0, "timeout", True)
    captured_sources = []

    def fake_collect_all(root, raw_store, sources, now, live_network, only_sources=None, deadline=None):
        captured_sources.extend(sorted(only_sources or []))
        return [make_item(url="https://example.com/rss")], {"rss": 1}, []

    monkeypatch.setattr("frontier_radar.jobs.collect_all", fake_collect_all)

    result = run_retry_failed(tmp_path, now="2026-06-22T17:00:00+00:00")

    assert captured_sources == ["rss"]
    assert result.status == "ok"
    assert result.counts["rss"] == 1
    assert len(db.list_items()) == 1


def test_retry_failed_does_not_duplicate_seen_items(tmp_path, monkeypatch):
    write_config(tmp_path, "github:\n  enabled: true\n  queries: ['agent']\n")
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    db.upsert_items([make_item()])
    run_id = db.record_run(
        "2026-06-22T15:00:00+00:00",
        "2026-06-22T15:01:00+00:00",
        "partial",
        {"github": 0},
        ["github: timeout"],
        [],
        job_type="daily",
        effective_config={},
    )
    db.record_source_run(run_id, "github", "timeout", 0, "timeout", True)
    monkeypatch.setattr(
        "frontier_radar.jobs.collect_all",
        lambda *args, **kwargs: ([make_item()], {"github": 1}, []),
    )

    result = run_retry_failed(tmp_path, now="2026-06-22T17:00:00+00:00")

    assert result.item_count == 0
    assert len(db.list_items()) == 1


def test_enrich_updates_long_lived_wiki_pages_with_provenance(tmp_path):
    write_config(tmp_path, "manual:\n  enabled: false\n")
    raw = tmp_path / "raw/2026-06-22/github"
    raw.mkdir(parents=True)
    (raw / "item.json").write_text("{}", encoding="utf-8")
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    db.upsert_items([make_item()])

    result = run_enrich(
        tmp_path,
        now="2026-06-22T18:00:00+00:00",
        since="7d",
        budget_minutes=60,
        top_n=1,
    )

    page = tmp_path / "wiki/repos/example-agent.md"
    assert result.status == "ok"
    assert page.exists()
    assert "raw/2026-06-22/github/item.json" in page.read_text(encoding="utf-8")


def test_enrich_preserves_existing_claim_content(tmp_path):
    write_config(tmp_path, "manual:\n  enabled: false\n")
    claim = tmp_path / "wiki/claims/existing.md"
    claim.parent.mkdir(parents=True)
    claim.write_text("# Existing\n\nOld claim that must remain.\n", encoding="utf-8")
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    db.upsert_items(
        [
            NormalizedItem(
                source="manual",
                source_type="expert-note",
                title="Existing",
                url="https://example.com/claim",
                author="expert",
                published_at="2026-06-22T15:00:00+00:00",
                summary="claim about agents",
                raw_path="manual/x-notes.md",
                tags=["manual"],
                metrics={},
                metadata={},
            )
        ]
    )
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual/x-notes.md").write_text("note", encoding="utf-8")

    run_enrich(tmp_path, now="2026-06-22T18:00:00+00:00", top_n=1)

    text = claim.read_text(encoding="utf-8")
    assert "Old claim that must remain." in text
    assert "https://example.com/claim" in text


def test_health_reports_wiki_lint_and_duplicate_items(tmp_path):
    write_config(tmp_path, "manual:\n  enabled: false\n")
    daily = tmp_path / "wiki/daily"
    daily.mkdir(parents=True)
    (daily / "today.md").write_text("# Bad\n\n- Claim without evidence\n", encoding="utf-8")

    result = run_health(tmp_path, now="2026-06-22T18:00:00+00:00")

    assert result.status == "error"
    assert any("wiki lint" in issue for issue in result.issues)


def test_state_vacuum_cleans_stale_locks_safely(tmp_path):
    write_config(
        tmp_path,
        "manual:\n  enabled: false\n",
        "maintenance:\n  stale_lock_after_minutes: 30\n",
    )
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    db.acquire_lock(
        "pipeline",
        "daily",
        "2026-06-22T15:00:00+00:00",
        stale_after_minutes=60,
    )

    result = run_state_vacuum(tmp_path, now="2026-06-22T16:00:00+00:00")

    assert result.status == "ok"
    assert result.cleaned_locks == ["pipeline"]
    assert db.active_locks() == []
