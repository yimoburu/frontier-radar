from pathlib import Path


def test_wiki_seed_layout_exists():
    root = Path(__file__).resolve().parents[1]
    for relative in [
        "wiki/index.md",
        "wiki/log.md",
        "wiki/sources.md",
        "wiki/daily/.gitkeep",
        "wiki/topics/.gitkeep",
        "wiki/entities/.gitkeep",
        "wiki/repos/.gitkeep",
        "wiki/papers/.gitkeep",
        "wiki/claims/.gitkeep",
        "raw/.gitkeep",
        "state/.gitkeep",
        "manual/.gitkeep",
    ]:
        assert (root / relative).exists(), relative


def test_scheduler_docs_are_harness_agnostic():
    root = Path(__file__).resolve().parents[1]
    cron = (root / "docs/scheduling/cron.md").read_text(encoding="utf-8")
    automation = (root / "docs/scheduling/agent-automation.md").read_text(encoding="utf-8")

    assert "frontier-radar daily" in cron
    assert "frontier-radar daily" in automation
    assert "frontier-radar retry-failed" in automation
    assert "frontier-radar enrich" in automation
    assert "frontier-radar health" in automation
    assert "America/Los_Angeles" in automation
    assert not (root / "docs/scheduling/codex.md").exists()


def test_readme_daily_schedule_does_not_name_a_specific_harness():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "agent automation" in readme
    for provider in ["Codex", "Claude Code", "OpenCode", "Gemini CLI", "Cursor"]:
        assert provider not in readme


def test_blueprint_docs_do_not_preserve_codex_automation_path():
    root = Path(__file__).resolve().parents[1]
    checked_paths = [
        "docs/superpowers/specs/2026-06-22-frontier-radar-design.md",
        "docs/superpowers/plans/2026-06-22-frontier-radar.md",
    ]
    forbidden_phrases = [
        "Codex app automation",
        "Codex automation",
        "Codex daily automation",
    ]

    for relative in checked_paths:
        text = (root / relative).read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            assert phrase not in text, f"{relative} contains {phrase!r}"
