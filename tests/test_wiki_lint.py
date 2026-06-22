from frontier_radar.wiki.lint import lint_wiki


def test_lint_wiki_accepts_digest_with_provenance(tmp_path):
    daily = tmp_path / "wiki" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-06-22.md").write_text(
        "# Frontier Radar Daily - 2026-06-22\n\n"
        "- [Agent Framework](https://github.com/example/agent-framework) "
        "(raw: `raw/2026-06-22/github/item.json`)\n",
        encoding="utf-8",
    )

    result = lint_wiki(tmp_path)

    assert result.ok is True
    assert result.errors == []


def test_lint_wiki_flags_missing_provenance(tmp_path):
    daily = tmp_path / "wiki" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-06-22.md").write_text(
        "# Daily\n\n- Claim without evidence\n",
        encoding="utf-8",
    )

    result = lint_wiki(tmp_path)

    assert result.ok is False
    assert "missing provenance" in result.errors[0]
