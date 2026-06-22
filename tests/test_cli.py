from frontier_radar.cli import main


def test_cli_sources_list_resolves_relative_root_from_current_cwd(tmp_path, monkeypatch, capsys):
    root = tmp_path / "relroot"
    (root / "config").mkdir(parents=True)
    (root / "config" / "sources.yaml").write_text("manual:\n  enabled: true\n", encoding="utf-8")
    (root / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--root", "relroot", "sources", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "manual" in captured.out


def test_cli_sources_list_prints_configured_sources(capsys):
    exit_code = main(["sources", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "github" in captured.out


def test_cli_sources_list_reports_missing_config_without_traceback(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path / "missing"), "sources", "list"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert captured.out == ""
    assert "ERROR:" in captured.err
    assert "Traceback" not in captured.err


def test_cli_wiki_lint_returns_zero_for_empty_wiki(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "wiki", "lint"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wiki lint passed" in captured.out


def test_cli_wiki_lint_errors_go_to_stderr(tmp_path, capsys):
    daily = tmp_path / "wiki" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-06-22.md").write_text("# Daily\n\n- Claim without evidence\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "wiki", "lint"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert captured.out == ""
    assert "missing provenance" in captured.err


def test_cli_digest_uses_valid_date_for_empty_digest(tmp_path, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text("manual:\n  enabled: false\n", encoding="utf-8")
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")

    exit_code = main(["--root", str(tmp_path), "digest"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "wiki/daily/" in captured.out
