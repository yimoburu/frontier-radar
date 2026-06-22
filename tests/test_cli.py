from frontier_radar.cli import main


def test_cli_sources_list_prints_configured_sources(capsys):
    exit_code = main(["sources", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "github" in captured.out


def test_cli_wiki_lint_returns_zero_for_empty_wiki(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "wiki", "lint"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wiki lint passed" in captured.out


def test_cli_digest_uses_valid_date_for_empty_digest(tmp_path, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text("manual:\n  enabled: false\n", encoding="utf-8")
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "digest"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "wiki/daily/" in captured.out
