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
    codex = (root / "docs/scheduling/codex.md").read_text(encoding="utf-8")

    assert "frontier-radar daily" in cron
    assert "frontier-radar daily" in codex
    assert "America/Los_Angeles" in codex
