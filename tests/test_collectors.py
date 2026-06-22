from pathlib import Path

import pytest

from frontier_radar.collectors.github import collect_github, parse_github_search
from frontier_radar.collectors.hn import parse_hn_search
from frontier_radar.collectors.rss import collect_rss, parse_feed
from frontier_radar.collectors.manual import collect_manual_notes
from frontier_radar.raw import RawStore


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


def test_parse_feed_prefers_atom_alternate_link_over_self_link():
    xml = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example Feed</title>
      <entry>
        <title>New model release</title>
        <link rel="self" href="https://example.com/feed-entry.xml"/>
        <link rel="alternate" href="https://example.com/model"/>
        <author><name>Example Lab</name></author>
        <updated>2026-06-22T12:00:00Z</updated>
        <summary>Frontier model release notes.</summary>
      </entry>
    </feed>'''

    items = parse_feed(xml, source="rss", source_name="Example Feed", raw_path="raw/feed.xml")

    assert items[0].url == "https://example.com/model"


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


def test_collect_manual_notes_rejects_directory_traversal(tmp_path):
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)

    with pytest.raises(ValueError):
        collect_manual_notes(tmp_path, "../outside")


def test_collect_manual_notes_skips_symlinked_files_outside_manual_directory(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "safe.md").write_text(
        "- 2026-06-22 | Safe Author | https://example.com/safe | Safe note\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside.md"
    outside.write_text(
        "- 2026-06-22 | Outside Author | https://example.com/outside | Outside note\n",
        encoding="utf-8",
    )
    (manual / "outside.md").symlink_to(outside)

    items = collect_manual_notes(tmp_path, "manual")

    assert [item.url for item in items] == ["https://example.com/safe"]


def test_collect_rss_continues_after_malformed_feed(tmp_path, monkeypatch):
    valid_xml = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example Feed</title>
      <entry>
        <title>Later valid item</title>
        <link href="https://example.com/later"/>
        <author><name>Example Lab</name></author>
        <updated>2026-06-22T12:00:00Z</updated>
        <summary>Recovered after a bad feed.</summary>
      </entry>
    </feed>'''

    def fake_fetch_bytes(url):
        if url == "https://example.com/bad.xml":
            return b"<feed>"
        return valid_xml

    monkeypatch.setattr("frontier_radar.collectors.rss.fetch_bytes", fake_fetch_bytes)

    errors = []

    items = collect_rss(
        {
            "feeds": [
                {"name": "Bad Feed", "url": "https://example.com/bad.xml"},
                {"name": "Good Feed", "url": "https://example.com/good.xml"},
            ]
        },
        RawStore(tmp_path),
        now="2026-06-22T15:00:00+00:00",
        errors=errors,
    )

    assert [item.title for item in items] == ["Later valid item"]
    assert items[0].raw_path == "raw/2026-06-22/rss/20260622T150000Z-1.xml"
    assert len(errors) == 1
    assert errors[0].startswith("rss feed Bad Feed:")


def test_collect_github_records_query_errors_and_continues(tmp_path, monkeypatch):
    valid_payload = b'''{
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
                "updated_at": "2026-06-22T12:00:00Z"
            }
        ]
    }'''

    def fake_fetch_bytes(url):
        if "bad-query" in url:
            return b"{"
        return valid_payload

    monkeypatch.setattr("frontier_radar.collectors.github.fetch_bytes", fake_fetch_bytes)
    errors = []

    items = collect_github(
        {"queries": ["bad-query", "good-query"], "per_query": 1},
        RawStore(tmp_path),
        now="2026-06-22T15:00:00+00:00",
        errors=errors,
    )

    assert [item.title for item in items] == ["example/agent-framework"]
    assert len(errors) == 1
    assert errors[0].startswith("github query bad-query:")
