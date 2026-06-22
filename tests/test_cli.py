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


def test_cli_fetch_collects_without_writing_digest(tmp_path, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "manual:\n  enabled: true\n  directory: manual\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "x-notes.md").write_text(
        "- 2026-06-22 | Expert | https://x.com/example/status/1 | agent note\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "fetch"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Frontier Radar fetch ok: 1 items" in captured.out
    assert not (tmp_path / "wiki" / "daily").exists()


def test_cli_daily_prints_human_reviewable_change_summary(tmp_path, capsys):
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
        "- 2026-06-22 | Expert | https://x.com/example/status/reviewable | agent review note\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(tmp_path), "daily"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Review summary:" in captured.out
    assert "- Changed: 1 new, 0 refreshed" in captured.out
    assert "- Output: wiki/daily/" in captured.out
    assert "- Why: ranked by freshness, momentum, relevance, novelty, source_weight" in captured.out
    assert "agent review note" in captured.out
    assert "relevance=" in captured.out


def test_cli_sources_check_reports_unreachable_feed(tmp_path, monkeypatch, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "rss:\n"
        "  enabled: true\n"
        "  feeds:\n"
        "    - name: Bad Feed\n"
        "      url: https://example.com/bad.xml\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")

    def fail_fetch(url, timeout=10):
        raise OSError("boom")

    monkeypatch.setattr("frontier_radar.cli.fetch_bytes", fail_fetch)

    exit_code = main(["--root", str(tmp_path), "sources", "check"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "Bad Feed" in captured.err


def test_cli_sources_check_accepts_reachable_feed(tmp_path, monkeypatch, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "rss:\n"
        "  enabled: true\n"
        "  feeds:\n"
        "    - name: Good Feed\n"
        "      url: https://example.com/good.xml\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")
    monkeypatch.setattr("frontier_radar.cli.fetch_bytes", lambda url, timeout=10: b"<rss />")

    exit_code = main(["--root", str(tmp_path), "sources", "check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "checked" in captured.out


def test_cli_sources_check_probes_query_source_reachability(tmp_path, monkeypatch, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "github:\n"
        "  enabled: true\n"
        "  queries: ['agent framework']\n"
        "hn:\n"
        "  enabled: true\n"
        "  queries: ['LLM']\n"
        "arxiv:\n"
        "  enabled: true\n"
        "  queries: ['large language models']\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")
    seen_urls = []

    def record_fetch(url, timeout=10):
        seen_urls.append(url)
        return b"{}"

    monkeypatch.setattr("frontier_radar.cli.fetch_bytes", record_fetch)

    exit_code = main(["--root", str(tmp_path), "sources", "check"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert any("api.github.com/search/repositories" in url for url in seen_urls)
    assert any("hn.algolia.com/api/v1/search_by_date" in url for url in seen_urls)
    assert any("export.arxiv.org/api/query" in url for url in seen_urls)


def test_cli_sources_check_reports_unreachable_query_source(tmp_path, monkeypatch, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "sources.yaml").write_text(
        "github:\n"
        "  enabled: true\n"
        "  queries: ['agent framework']\n",
        encoding="utf-8",
    )
    (tmp_path / "config" / "topics.yaml").write_text("topics: {}\n", encoding="utf-8")

    def fail_fetch(url, timeout=10):
        raise OSError("blocked")

    monkeypatch.setattr("frontier_radar.cli.fetch_bytes", fail_fetch)

    exit_code = main(["--root", str(tmp_path), "sources", "check"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "github" in captured.err
