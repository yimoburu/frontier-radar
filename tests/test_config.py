from pathlib import Path

from frontier_radar.config import AppConfig, load_app_config, repo_root


def test_repo_root_points_to_project_directory():
    assert (repo_root() / "pyproject.toml").exists()


def test_load_app_config_reads_sources_and_topics():
    config = load_app_config(Path("config/sources.yaml"), Path("config/topics.yaml"))

    assert isinstance(config, AppConfig)
    assert config.sources["github"]["enabled"] is True
    assert "agents-and-tool-use" in config.topics["topics"]
