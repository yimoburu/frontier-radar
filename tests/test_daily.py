from pathlib import Path

from frontier_radar.models import NormalizedItem
from frontier_radar.daily import DailyResult, run_daily
from frontier_radar.storage import Database


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


def test_run_daily_uses_configured_llm_brief(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "manual:\n  enabled: true\n  directory: manual\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text(
        "topics:\n  agents:\n    keywords: ['agent']\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "llm.yaml").write_text(
        "enabled: true\n"
        "provider: openai-compatible\n"
        "base_url: https://llm.example/v1\n"
        "model: frontier-synth\n"
        "api_key_env: TEST_LLM_KEY\n",
        encoding="utf-8",
    )
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "x-notes.md").write_text(
        "- 2026-06-22 | Expert | https://x.com/example/status/llm | agent synthesis note\n",
        encoding="utf-8",
    )
    captured = {}

    def fake_synthesize(ranked_items, settings):
        captured["api_key"] = settings.api_key
        captured["titles"] = [entry.item.title for entry in ranked_items]
        return type(
            "Result",
            (),
            {
                "used_llm": True,
                "lines": [
                    "- LLM synthesis: agent notes should become a wiki claim. Provenance: `manual/x-notes.md`"
                ],
                "error": "",
            },
        )()

    monkeypatch.setenv("TEST_LLM_KEY", "secret")
    monkeypatch.setattr("frontier_radar.daily.synthesize_daily_brief", fake_synthesize)

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    digest = (tmp_path / result.digest_path).read_text(encoding="utf-8")
    assert result.status == "ok"
    assert captured["api_key"] == "secret"
    assert captured["titles"] == ["agent synthesis note"]
    assert "LLM synthesis: agent notes should become a wiki claim" in digest


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


def test_run_daily_records_bad_manual_rows_without_aborting(tmp_path):
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
        "- bad-date | Expert | https://x.com/example/status/bad | bad agent note\n"
        "- 2026-06-22 | Expert | https://x.com/example/status/good | good agent note\n",
        encoding="utf-8",
    )

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    assert result.status == "partial"
    assert result.counts["manual"] == 1
    assert any("invalid date" in error for error in result.errors)
    digest = (tmp_path / result.digest_path).read_text(encoding="utf-8")
    assert "good agent note" in digest
    assert "bad agent note" not in digest


def test_run_daily_ranks_current_run_items_not_stale_history(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "manual:\n  enabled: true\n  directory: manual\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text(
        "topics:\n  agents:\n    keywords: ['agent']\n",
        encoding="utf-8",
    )
    db = Database(tmp_path / "state" / "frontier-radar.sqlite")
    db.init()
    db.upsert_items(
        [
            NormalizedItem(
                source="github",
                source_type="repo",
                title="Old agent powerhouse",
                url="https://example.com/old",
                author="old",
                published_at="2026-06-22T14:00:00+00:00",
                summary="agent framework with many stars",
                raw_path="raw/2026-06-22/github/old.json",
                tags=["Python"],
                metrics={"stars": 100000},
                metadata={},
            )
        ]
    )
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "x-notes.md").write_text(
        "- 2026-06-22 | Expert | https://x.com/example/status/new | new agent note\n",
        encoding="utf-8",
    )

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    digest = (tmp_path / result.digest_path).read_text(encoding="utf-8")
    assert "new agent note" in digest
    assert "Old agent powerhouse" not in digest


def test_run_daily_deduplicates_current_run_urls(tmp_path):
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
        "- 2026-06-22 | Expert | https://x.com/example/status/dup | duplicate agent note\n"
        "- 2026-06-22 | Expert | https://x.com/example/status/dup | duplicate agent note\n",
        encoding="utf-8",
    )

    result = run_daily(tmp_path, now="2026-06-22T15:00:00+00:00", live_network=False)

    assert result.status == "ok"
    assert result.top_titles == ["duplicate agent note"]
