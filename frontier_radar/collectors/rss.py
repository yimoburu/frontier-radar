from __future__ import annotations

import xml.etree.ElementTree as ET

from frontier_radar.collectors.base import fetch_bytes
from frontier_radar.models import NormalizedItem
from frontier_radar.raw import RawStore


ATOM = "{http://www.w3.org/2005/Atom}"


def text(node: ET.Element | None, default: str = "") -> str:
    return "".join(node.itertext()).strip() if node is not None else default


def parse_feed(xml: bytes, source: str, source_name: str, raw_path: str) -> list[NormalizedItem]:
    root = ET.fromstring(xml)
    items: list[NormalizedItem] = []
    if root.tag == f"{ATOM}feed":
        for entry in root.findall(f"{ATOM}entry"):
            link_node = entry.find(f"{ATOM}link")
            link = link_node.attrib.get("href", "") if link_node is not None else ""
            author = text(entry.find(f"{ATOM}author/{ATOM}name"), source_name)
            items.append(
                NormalizedItem(
                    source=source,
                    source_type="feed",
                    title=text(entry.find(f"{ATOM}title")),
                    url=link,
                    author=author,
                    published_at=text(entry.find(f"{ATOM}updated"), "1970-01-01T00:00:00+00:00"),
                    summary=text(entry.find(f"{ATOM}summary")),
                    raw_path=raw_path,
                    tags=[source_name],
                    metrics={},
                    metadata={"feed": source_name},
                )
            )
    else:
        for entry in root.findall("./channel/item"):
            items.append(
                NormalizedItem(
                    source=source,
                    source_type="feed",
                    title=text(entry.find("title")),
                    url=text(entry.find("link")),
                    author=text(entry.find("author"), source_name),
                    published_at=text(entry.find("pubDate"), "1970-01-01T00:00:00+00:00"),
                    summary=text(entry.find("description")),
                    raw_path=raw_path,
                    tags=[source_name],
                    metrics={},
                    metadata={"feed": source_name},
                )
            )
    return [item for item in items if item.url and item.title]


def collect_rss(config: dict, raw_store: RawStore, now: str, source: str = "rss") -> list[NormalizedItem]:
    results: list[NormalizedItem] = []
    for feed in config.get("feeds", []):
        xml = fetch_bytes(feed["url"])
        raw_path = raw_store.write_snapshot(source, "xml", xml, now=now)
        results.extend(parse_feed(xml, source=source, source_name=feed["name"], raw_path=str(raw_path)))
    return results
