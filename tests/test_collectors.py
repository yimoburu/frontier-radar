from pathlib import Path

from frontier_radar.collectors.github import parse_github_search
from frontier_radar.collectors.hn import parse_hn_search
from frontier_radar.collectors.rss import parse_feed
from frontier_radar.collectors.manual import collect_manual_notes


def test_parse_github_search_normalizes_repo_items():
    payload = {
        "items": [
            {
                "full_name": "example/agent-framework",
                "html_url": "https://github.com/example/agent-framework",
                "description": "AI agent framework",
                "stargazers_count": 321,
                "forks_count": 12,
                "language": "Python",
                "owner": {"login": "example"},
                "created_at": "2026-06-20T00:00:00Z",
                "updated_at": "2026-06-22T12:00:00Z",
            }
        ]
    }

    items = parse_github_search(payload, "raw/github.json")

    assert items[0].title == "example/agent-framework"
    assert items[0].metrics["stars"] == 321
    assert items[0].tags == ["Python"]


def test_parse_hn_search_normalizes_discussions():
    payload = {
        "hits": [
            {
                "title": "AI agents",
                "url": "https://example.com",
                "author": "alice",
                "created_at": "2026-06-22T12:00:00Z",
                "points": 50,
                "num_comments": 9,
                "objectID": "1",
            }
        ]
    }

    items = parse_hn_search(payload, "raw/hn.json")

    assert items[0].source_type == "discussion"
    assert items[0].metrics["points"] == 50
    assert items[0].url == "https://example.com"


def test_parse_feed_handles_atom_entries():
    xml = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example Feed</title>
      <entry>
        <title>New model release</title>
        <link href="https://example.com/model"/>
        <author><name>Example Lab</name></author>
        <updated>2026-06-22T12:00:00Z</updated>
        <summary>Frontier model release notes.</summary>
      </entry>
    </feed>'''

    items = parse_feed(xml, source="rss", source_name="Example Feed", raw_path="raw/feed.xml")

    assert items[0].title == "New model release"
    assert items[0].author == "Example Lab"


def test_collect_manual_notes_reads_markdown_links(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "x-notes.md").write_text(
        "- 2026-06-22 | Andrej Karpathy | https://x.com/example/status/1 | Notes on LLM wiki memory\n",
        encoding="utf-8",
    )

    items = collect_manual_notes(tmp_path, "manual")

    assert items[0].source == "manual"
    assert items[0].source_type == "expert-note"
    assert "LLM wiki memory" in items[0].summary
