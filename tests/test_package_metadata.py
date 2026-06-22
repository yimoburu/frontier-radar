from pathlib import Path


def test_package_exports_version():
    import frontier_radar

    assert frontier_radar.__version__ == "0.1.0"


def test_console_script_target_is_importable():
    from frontier_radar.cli import main

    assert callable(main)


def test_harness_files_delegate_to_agents_contract():
    root = Path(__file__).resolve().parents[1]
    agents = (root / "AGENTS.md").read_text()
    claude = (root / "CLAUDE.md").read_text()
    codex = (root / "CODEX.md").read_text()

    assert "canonical contract" in agents
    assert "AGENTS.md" in claude
    assert "AGENTS.md" in codex


def test_readme_referenced_scheduling_directory_exists():
    root = Path(__file__).resolve().parents[1]

    assert (root / "docs" / "scheduling").is_dir()
