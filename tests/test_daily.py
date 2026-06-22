from pathlib import Path

from frontier_radar.daily import DailyResult, run_daily


def test_run_daily_writes_digest_with_fixture_items(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "manual:\n  enabled: true\n  directory: manual\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text(
        "topics:\n  agents:\n    keywords: ['agent']\n",
        encoding="utf-8",
    )
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "x-notes.md").write_text(
        "- 2026-06-22 | Expert | https://x.com/example/status/1 | agent memory notes\n",
        encoding="utf-8",
    )

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    assert isinstance(result, DailyResult)
    assert result.status == "ok"
    assert result.digest_path == Path("wiki/daily/2026-06-22.md")
    assert "agent memory notes" in (tmp_path / result.digest_path).read_text(encoding="utf-8")


def test_run_daily_resolves_relative_root_from_cwd(tmp_path, monkeypatch):
    root = tmp_path / "relroot"
    (root / "config").mkdir(parents=True)
    (root / "config" / "sources.yaml").write_text(
        "manual:\n  enabled: true\n  directory: manual\n",
        encoding="utf-8",
    )
    (root / "config" / "topics.yaml").write_text(
        "topics:\n  agents:\n    keywords: ['agent']\n",
        encoding="utf-8",
    )
    (root / "manual").mkdir()
    (root / "manual" / "x-notes.md").write_text(
        "- 2026-06-22 | Expert | https://x.com/example/status/2 | relative agent note\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_daily(
        Path("relroot"),
        now="2026-06-22T15:00:00+00:00",
        live_network=False,
    )

    assert result.status == "ok"
    assert result.digest_path == Path("wiki/daily/2026-06-22.md")
    digest = root / result.digest_path
    assert digest.exists()
    assert "relative agent note" in digest.read_text(encoding="utf-8")


def test_run_daily_records_manual_collector_errors(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "manual:\n  enabled: true\n  directory: ../outside\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    assert result.status == "error"
    assert result.counts["manual"] == 0
    assert any("manual:" in error for error in result.errors)
