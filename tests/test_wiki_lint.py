from frontier_radar.wiki.lint import lint_wiki
from frontier_radar.wiki.render import write_daily_digest

from test_wiki_render import ranked_item


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


def test_lint_wiki_accepts_digest_written_by_renderer(tmp_path):
    write_daily_digest(tmp_path, "2026-06-22", [ranked_item()], {"github": 1}, [])

    result = lint_wiki(tmp_path)

    assert result.ok is True
    assert result.errors == []


def test_lint_wiki_accepts_rendered_digest_with_url_error(tmp_path):
    write_daily_digest(
        tmp_path,
        "2026-06-22",
        [ranked_item()],
        {"github": 1},
        ["fetch failed for https://api.example.test/items"],
    )

    result = lint_wiki(tmp_path)

    assert result.ok is True
    assert result.errors == []


def test_lint_wiki_accepts_rendered_digest_with_sanitized_item_url(tmp_path):
    write_daily_digest(
        tmp_path,
        "2026-06-22",
        [ranked_item(url="https://example.test/path)\n- injected")],
        {"github": 1},
        [],
    )

    markdown = (tmp_path / "wiki" / "daily" / "2026-06-22.md").read_text(
        encoding="utf-8"
    )
    result = lint_wiki(tmp_path)

    assert "\n- injected" not in markdown
    assert "path%29 - injected" in markdown
    assert result.ok is True
    assert result.errors == []
